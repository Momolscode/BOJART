"""Orchestrateur reproductible « demande → figurine → visualisation → tranchage ».

État persistant par tâche (state.json), identifiant déterministe (doublon = même tâche,
aucun recalcul), reprise après interruption, trois tentatives maximum par étape,
manifeste final avec empreintes. Aucune commande machine n'est jamais émise.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import checks, fabrication, sculpt, slicing
from .spec import SpecRejected, parse_request

PIPELINE_VERSION = 'bojart.figurine.pipeline.v1'
MAX_ATTEMPTS = 3
STEPS = ['intake', 'transcription', 'spec', 'pose_study', 'geometry', 'assembly', 'checks',
         'renders', 'exports', 'slicing', 'manifest']
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]


class Interrupted(RuntimeError):
    """Interruption simulée (injection de panne) entre deux étapes."""


class Blocked(RuntimeError):
    """Dépendance absente : l'étape est BLOQUÉE, jamais transformée en succès."""


def _canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def _git_commit():
    """Commit courant et état du code de la chaîne (un code non commité est signalé)."""
    try:
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = subprocess.run(['git', 'status', '--porcelain', '--', 'jarvis/apps/jarvis/app', 'jarvis/tools'],
                               cwd=REPO, capture_output=True, text=True, timeout=10).stdout.strip()
        return {'head': head or None, 'pipeline_code_modified_since_commit': bool(dirty)}
    except Exception:
        return {'head': None, 'pipeline_code_modified_since_commit': None}


def environment():
    def ver(dist):
        from importlib import metadata
        try:
            return metadata.version(dist)
        except metadata.PackageNotFoundError:
            return None
    blender = shutil.which('blender')
    gpu = shutil.which('nvidia-smi')
    return {
        'python': sys.version.split()[0], 'platform': platform.platform(), 'cpu_count': os.cpu_count(),
        'numpy': ver('numpy'), 'trimesh': ver('trimesh'), 'scikit-image': ver('scikit-image'),
        'manifold3d': ver('manifold3d'), 'scipy': ver('scipy'), 'rtree': ver('rtree'), 'matplotlib': ver('matplotlib'),
        'slicer': slicing.slicer_version(slicing.find_slicer()) if slicing.find_slicer() else None,
        'blender': subprocess.run([blender, '--version'], capture_output=True, text=True, timeout=60).stdout.splitlines()[0] if blender else None,
        'gpu': 'nvidia-smi présent' if gpu else 'aucun GPU détecté (calcul CPU uniquement)',
    }


class FigurineRun:
    def __init__(self, text, out_root: Path, *, source='typed', mesh: Path | None = None, audio: Path | None = None,
                 provenance: Path | None = None, voxel=0.6, faults=(), max_grid_mb=1500, render_size=900,
                 render_samples=32, task_id=None):
        self.text, self.source, self.mesh_in, self.audio = text, source, mesh, audio
        self.provenance = provenance
        self.voxel, self.faults, self.max_grid_mb = voxel, set(faults), max_grid_mb
        self.render_size, self.render_samples = render_size, render_samples
        self.out_root = Path(out_root)
        self.spec = None
        self.task_id = task_id
        self.dir = None
        self.state = None

    # ------------------------------------------------------------ identité et état
    def _identity(self, spec):
        mesh_hash = sha256_file(self.mesh_in) if self.mesh_in else None
        if self.mesh_in:
            spec['geometry_source'] = 'import'
        ident = {'spec': {k: spec[k] for k in ('character', 'pose_intent', 'height_mm', 'material', 'process')},
                 'mesh_sha256': mesh_hash, 'voxel': self.voxel, 'pipeline': PIPELINE_VERSION,
                 'sculpt': sculpt.SCULPT_VERSION, 'fab': fabrication.FAB_VERSION, 'checks': checks.CHECKS_VERSION}
        return hashlib.sha256(_canon(ident).encode()).hexdigest()[:16], ident

    def _save(self):
        tmp = self.dir / 'state.json.tmp'
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding='utf8')
        os.replace(tmp, self.dir / 'state.json')

    def _step(self, name):
        return self.state['steps'].setdefault(name, {'status': 'PENDING', 'attempts': 0})

    def _outputs_ok(self, st):
        for rel, digest in st.get('outputs', {}).items():
            p = self.dir / rel
            if not p.exists() or sha256_file(p) != digest:
                return False
        return True

    def _run_step(self, name, fn):
        st = self._step(name)
        if st['status'] in ('DONE', 'SKIPPED', 'NOT_TESTED') and self._outputs_ok(st):
            st['reused'] = True
            return st
        if st['status'] == 'BLOCKED' and not self.state.get('retry_blocked'):
            raise Blocked(st.get('reason', 'étape bloquée'))
        if st['attempts'] >= MAX_ATTEMPTS:
            st['status'] = 'FAILED'; st['reason'] = 'trois tentatives épuisées'; self._save()
            raise RuntimeError(f'{name} : trois tentatives épuisées')
        st.update(status='RUNNING', attempts=st['attempts'] + 1, started=_now()); st.pop('reused', None)
        self._save()
        t0 = time.perf_counter()
        try:
            result = fn() or {}
        except Blocked as exc:
            st.update(status='BLOCKED', reason=str(exc), seconds=round(time.perf_counter() - t0, 3)); self._save()
            raise
        except Exception as exc:
            st.update(status='FAILED', reason=f'{type(exc).__name__}: {exc}', seconds=round(time.perf_counter() - t0, 3))
            self._save(); raise
        status = result.pop('_status', 'DONE')
        outputs = result.pop('_outputs', [])
        st.update(status=status, seconds=round(time.perf_counter() - t0, 3), finished=_now(), result=result,
                  outputs={str(o): sha256_file(self.dir / o) for o in outputs},
                  peak_rss_mb_process=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                  peak_rss_mb_children=round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1))
        self._save()
        if f'interrupt_after:{name}' in self.faults and not self.state.get('interrupt_consumed', {}).get(name):
            self.state.setdefault('interrupt_consumed', {})[name] = True; self._save()
            raise Interrupted(f'interruption simulée après {name}')
        return st

    def _entry_point(self):
        """Même point d'entrée texte que l'application (dialogue.interpret), puis spécification."""
        if str(HERE.parent) not in sys.path:
            sys.path.insert(0, str(HERE.parent))
        from core import Rejected  # noqa: E402
        from dialogue import interpret  # noqa: E402
        try:
            decision = interpret(self.text)
        except Rejected as exc:
            cause = exc.__cause__
            if isinstance(cause, SpecRejected):
                raise cause
            status = 'REFUSED' if 'indisponible' in str(exc) else 'CLARIFY'
            raise SpecRejected(str(exc), status) from exc
        if decision['intent'] != 'create_figurine':
            raise SpecRejected(f"Intention « {decision['intent']} » : hors de la chaîne figurine.", 'NOT_FIGURINE')
        spec = decision['spec']
        if self.audio:
            spec = parse_request(self.text, source='voice_transcript')
        self.entry_decision = {k: decision.get(k) for k in ('intent', 'engine', 'provider', 'requires_confirmation', 'message')}
        return spec

    # ------------------------------------------------------------ exécution
    def run(self):
        t_receive = time.perf_counter()
        try:
            spec = self._entry_point()
        except SpecRejected as exc:
            return {'status': exc.status, 'message': str(exc), 'task_id': None,
                    'ack_seconds': round(time.perf_counter() - t_receive, 4)}
        self.spec = spec
        tid, ident = self._identity(spec)
        entry = getattr(self, 'entry_decision', None)
        self.task_id = tid
        self.dir = self.out_root / tid
        fresh = not (self.dir / 'state.json').exists()
        self.dir.mkdir(parents=True, exist_ok=True)
        if fresh:
            self.state = {'task_id': tid, 'identity': ident, 'created': _now(), 'requests': [], 'steps': {}}
        else:
            self.state = json.loads((self.dir / 'state.json').read_text(encoding='utf8'))
        self.state['requests'].append({'at': _now(), 'text': self.text, 'source': self.source, 'entry_point': entry,
                                       'faults': sorted(self.faults), 'duplicate_of_existing_task': not fresh})
        self.state['ack_seconds'] = round(time.perf_counter() - t_receive, 4)
        self._save()
        if self.state.get('status') == 'DONE' and self._outputs_ok(self._step('manifest')):
            return {'status': 'DONE', 'task_id': tid, 'dir': str(self.dir), 'duplicate': True,
                    'message': 'Commande déjà traitée : résultats existants renvoyés, aucun recalcul.'}
        try:
            for name in STEPS:
                self._run_step(name, getattr(self, '_s_' + name))
            self.state['status'] = 'DONE'
        except Interrupted as exc:
            self.state['status'] = 'INTERRUPTED'; self.state['message'] = str(exc)
        except Blocked as exc:
            self.state['status'] = 'BLOCKED'; self.state['message'] = str(exc)
        except Exception as exc:
            self.state['status'] = 'FAILED'; self.state['message'] = f'{type(exc).__name__}: {exc}'
        self._save()
        return {'status': self.state['status'], 'task_id': tid, 'dir': str(self.dir),
                'message': self.state.get('message'), 'duplicate': not fresh}

    # ------------------------------------------------------------ étapes
    def _s_intake(self):
        return {'received': _now(), 'source': self.source, 'text_length': len(self.text)}

    def _s_transcription(self):
        if not self.audio:
            return {'_status': 'NOT_TESTED',
                    'note': 'Aucun enregistrement disponible : texte injecté au même point d’entrée. '
                            'Reconnaissance vocale NON TESTÉE ; aucun score de confiance fabriqué.'}
        sys.path.insert(0, str(HERE.parent))
        from voice import LocalVoice  # noqa: E402
        cfg_dir = os.environ.get('BOJART_WHISPER_DIR', '')
        res = LocalVoice({'enabled': True, 'model_dir': cfg_dir}).transcribe(self.audio.read_bytes())
        return {'transcript': res.get('text'), 'engine': res.get('engine'), 'needs_review': True}

    def _s_spec(self):
        (self.dir / 'spec.json').write_text(json.dumps(self.spec, ensure_ascii=False, indent=1), encoding='utf8')
        return {'_outputs': ['spec.json'], 'character': self.spec['character']['label'],
                'geometry_source': self.spec['geometry_source']}

    def _s_pose_study(self):
        if self.spec['geometry_source'] != 'procedural_sdf':
            return {'_status': 'SKIPPED', 'reason': 'pas de sculpture procédurale : la pose vient du fichier fourni'}
        metrics = [sculpt.pose_proxy_metrics(p) for p in sculpt.pose_names()]
        wanted = {'iconic': None, 'combat': 'garde_basse', 'rest': 'repos_fier'}[self.spec['pose_intent']]
        chosen, notes = sculpt.choose_pose(metrics)
        if wanted:
            chosen, notes = wanted, notes + [f'Pose imposée par la demande ({self.spec["pose_intent"]}).']
        data = {'candidates': metrics, 'chosen': chosen, 'notes': notes, 'voxel_mm': 2.0}
        (self.dir / 'pose_study.json').write_text(json.dumps(data, ensure_ascii=False, indent=1, default=float), encoding='utf8')
        self.state['pose'] = chosen
        return {'_outputs': ['pose_study.json'], 'chosen': chosen}

    def _grid_mb(self):
        n = [int(150 / self.voxel) + 3, int(150 / self.voxel) + 3, int(241 / self.voxel) + 3]
        return n[0] * n[1] * n[2] * 4 / 1e6 + n[0] * n[1] * 24 * 12 / 1e6

    def _s_geometry(self):
        import trimesh
        out = self.dir / 'nominal.stl'
        if self.spec['geometry_source'] == 'import_required':
            raise Blocked(f"{self.spec['character']['label']} : personnage sous droits de tiers. Jarvis ne sculpte ni "
                          'ne rend sa ressemblance ; il faut un maillage fourni avec sa provenance et ses conditions '
                          'd’usage documentées (--mesh et --provenance). Étape BLOQUÉE.')
        if self.spec['geometry_source'] == 'import':
            third_party = self.spec['character']['rights'] == 'third_party_licensed'
            if third_party and not (self.provenance and self.provenance.is_file()):
                raise Blocked('Maillage d’un personnage tiers sans fiche de provenance/licence (--provenance) : '
                              'étape BLOQUÉE, aucun traitement du fichier.')
            mesh = trimesh.load(str(self.mesh_in), force='mesh')
            rep = fabrication.guarded_repair(mesh)
            info = {k: v for k, v in rep.items() if k != 'mesh'}
            if not rep['accepted']:
                (self.dir / 'repair_refused.json').write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding='utf8')
                raise RuntimeError('Maillage importé non réparable sans perte de fidélité : ' + str(rep['reason']))
            rep['mesh'].export(out)
            return {'_outputs': ['nominal.stl'], 'source': 'import', 'repair': info,
                    'input_sha256': sha256_file(self.mesh_in),
                    'provenance_sha256': sha256_file(self.provenance) if self.provenance else None}
        need = self._grid_mb()
        budget = 1 if 'low_memory' in self.faults else self.max_grid_mb
        if need > budget:
            raise Blocked(f'Mémoire insuffisante : grille estimée {need:.0f} Mo > budget {budget} Mo. '
                          'Augmenter le pas de voxel (qualité moindre, à annoncer) ou la mémoire. Étape BLOQUÉE.')
        mesh, bodies = sculpt.sculpt_figure(self.state['pose'], voxel=self.voxel)
        mesh.export(out)
        return {'_outputs': ['nominal.stl'], 'source': 'procedural_sdf', 'pose': self.state['pose'],
                'voxel_mm': self.voxel, 'grid_estimate_mb': round(need), 'bodies': bodies,
                'triangles': int(len(mesh.faces))}

    def _s_assembly(self):
        import trimesh
        nominal = trimesh.load(str(self.dir / 'nominal.stl'))
        asm = fabrication.build_assembly(nominal, self.spec['height_mm'])
        asm['figurine'].export(self.dir / 'figurine.stl'); asm['socle'].export(self.dir / 'socle.stl')
        (self.dir / 'assembly.json').write_text(json.dumps(asm['info'], ensure_ascii=False, indent=1), encoding='utf8')
        res = {'_outputs': ['figurine.stl', 'socle.stl', 'assembly.json']}
        fits = all(e <= b for e, b in zip(sorted(asm['figurine'].extents), sorted(slicing.SIM_BED_MM)))
        if not fits:
            plan = fabrication.plan_cuts(asm['figurine'], slicing.SIM_BED_MM)
            (self.dir / 'cut_plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf8')
            res['_outputs'].append('cut_plan.json'); res['cut_pieces'] = len(plan['pieces'])
        return res

    def _s_checks(self):
        import trimesh
        fig = trimesh.load(str(self.dir / 'figurine.stl')); base = trimesh.load(str(self.dir / 'socle.stl'))
        info = json.loads((self.dir / 'assembly.json').read_text(encoding='utf8'))
        total = trimesh.util.concatenate([fig, base])
        base_print = base.copy()
        if info.get('base_recess_height_mm'):
            base_print.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
        report = {
            'thresholds': checks.THRESHOLDS,
            'parts': [checks.check_part(fig, 'figurine', thickness_samples=1500),
                      checks.check_part(base_print, 'socle', thickness_samples=600)],
            'orientation_note': 'surplombs mesurés dans l’orientation d’impression (socle retourné s’il est évidé)',
            'assembly_height': {'measured_mm': round(float(total.extents[2]), 3), 'target_mm': self.spec['height_mm']},
            'stability': checks.check_stability(fig, base, info),
            'fit': checks.check_fit(fig, base, info),
        }
        thin = report['parts'][0]['measured'].get('thickness_mm', {}).get('p1')
        report['detail_vs_process'] = checks.detail_vs_process(thin or 0, self.spec['process'], self.spec['nozzle_mm'] or 0.05)
        elim = [f"{p['part']}: {e}" for p in report['parts'] for e in p['eliminatory']]
        if abs(total.extents[2] - self.spec['height_mm']) / self.spec['height_mm'] > checks.THRESHOLDS['height_tolerance_rel']:
            elim.append('hauteur totale hors tolérance')
        if not report['stability']['stable_static_estimate']:
            elim.append('stabilité estimée insuffisante')
        if not report['fit']['fit_ok']:
            elim.append('interférence tenon/logement')
        report['eliminatory'] = elim
        report['verdict'] = 'CONFORME_AUX_CRITERES_CALCULES' if not elim else 'NON_CONFORME'
        (self.dir / 'checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf8')
        if elim:
            raise RuntimeError('Contrôles éliminatoires : ' + '; '.join(elim))
        return {'_outputs': ['checks.json'], 'verdict': report['verdict']}

    def _s_renders(self):
        blender = shutil.which('blender')
        if 'no_blender' in self.faults or not blender:
            raise Blocked('Blender absent : rendus non produits (aucune image substituée). Étape BLOQUÉE.')
        rd = self.dir / 'rendus'; rd.mkdir(exist_ok=True)
        cmd = [blender, '-b', '--factory-startup', '--python', str(HERE / 'blender_render.py'), '--',
               str(rd), str(self.render_size), str(self.render_samples), str(self.dir / 'figurine.stl'), str(self.dir / 'socle.stl')]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if 'BOJART_RENDER_OK' not in proc.stdout:
            raise RuntimeError('Rendu Blender échoué : ' + (proc.stdout + proc.stderr)[-600:])
        outs = sorted(str(p.relative_to(self.dir)) for p in rd.iterdir() if p.suffix in ('.png', '.blend'))
        return {'_outputs': outs, 'engine': 'Cycles CPU', 'samples': self.render_samples,
                'note': 'rendus argile sans texture + vue maillage ; appréciation visuelle, pas une mesure'}

    def _s_exports(self):
        import trimesh
        parts = {'figurine': trimesh.load(str(self.dir / 'figurine.stl')), 'socle': trimesh.load(str(self.dir / 'socle.stl'))}
        r = slicing.export_3mf(parts, self.dir / 'projet.3mf')
        if r['status'] != 'DONE':
            raise RuntimeError('Export 3MF incomplet')
        return {'_outputs': ['projet.3mf'], **r}

    def _s_slicing(self):
        plan = self.dir / 'cut_plan.json'
        if plan.exists():
            n = len(json.loads(plan.read_text(encoding='utf8'))['pieces'])
            raise Blocked(f'Figurine plus grande que le volume d’hypothèse {slicing.SIM_BED_MM} mm : étude de découpe '
                          f'en {n} pièces produite (cut_plan.json), clés d’assemblage et parc réel non définis. '
                          'Tranchage par pièce non réalisé : étape BLOQUÉE.')
        sd = self.dir / 'tranchage'; sd.mkdir(exist_ok=True)
        fault = 'slicer_missing' if 'slicer_missing' in self.faults else ('slicer_fail' if 'slicer_fail' in self.faults else None)
        results, outs = {}, []
        import trimesh
        info = json.loads((self.dir / 'assembly.json').read_text(encoding='utf8'))
        sources = {'figurine': self.dir / 'figurine.stl', 'socle': self.dir / 'socle.stl'}
        if info.get('base_recess_height_mm'):
            flipped = trimesh.load(str(self.dir / 'socle.stl'))
            flipped.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
            flipped.apply_translation([0, 0, -flipped.bounds[0][2]])
            sources['socle'] = sd / 'socle_impression.stl'
            flipped.export(sources['socle'])
        for part in ('socle', 'figurine'):
            try:
                r = slicing.slice_part(sources[part], sd, fault=fault)
            except slicing.SlicerUnavailable as exc:
                raise Blocked(str(exc))
            if r['status'] != 'DONE':
                (sd / f'{part}_echec.json').write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding='utf8')
                raise RuntimeError(f'Tranchage {part} en échec (code {r["returncode"]}) ; aucun chiffre substitué.')
            results[part] = r; outs.append(f'tranchage/{r["gcode"]}')
        prev = slicing.layer_previews(sd / results['figurine']['gcode'], sd / 'apercu_couches_figurine.png')
        outs += ['tranchage/apercu_couches_figurine.png', 'tranchage/profil_simulation.ini']
        (sd / 'tranchage.json').write_text(json.dumps({'parts': results, 'preview': prev, 'profile': slicing.PROFILE,
                                                       'bed_hypothesis_mm': slicing.SIM_BED_MM}, ensure_ascii=False, indent=1), encoding='utf8')
        outs.append('tranchage/tranchage.json')
        return {'_outputs': outs, 'estimates': {p: r['stats'] for p, r in results.items()},
                'sent_to_machine': False}

    def _s_manifest(self):
        files = {}
        for p in sorted(self.dir.rglob('*')):
            if p.is_file() and p.name not in ('state.json', 'state.json.tmp', 'manifest.json'):
                files[str(p.relative_to(self.dir))] = {'sha256': sha256_file(p), 'bytes': p.stat().st_size}
        steps = {k: {kk: v.get(kk) for kk in ('status', 'seconds', 'attempts', 'reason')}
                 for k, v in self.state['steps'].items() if k != 'manifest'}
        manifest = {
            'task_id': self.task_id, 'created': self.state['created'], 'finished': _now(),
            'commit': _git_commit(), 'pipeline': PIPELINE_VERSION, 'environment': environment(),
            'request': self.text, 'spec': self.spec, 'identity': self.state['identity'],
            'hypotheses': {'height_mm': self.spec['field_origin']['height_mm'], 'fdm_profile': 'simulation, non vérifié',
                           'assembly': fabrication.ASSEMBLY_HYPOTHESES, 'bed_mm': slicing.SIM_BED_MM},
            'steps': steps,
            'executed': [k for k, v in steps.items() if v['status'] == 'DONE'],
            'not_tested_or_simulated': [k for k, v in steps.items() if v['status'] in ('NOT_TESTED', 'SKIPPED')]
                                       + ['impression physique (N3)', 'affichage sur la tour réelle', 'reconnaissance vocale'],
            'evidence_level': 'N2 — parcours numérique avec vrai maillage, rendus et tranchage réel ; pas d’impression',
            'files': files,
        }
        (self.dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf8')
        return {'_outputs': ['manifest.json'], 'files': len(files)}
