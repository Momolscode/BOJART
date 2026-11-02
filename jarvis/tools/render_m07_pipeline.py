#!/usr/bin/env python3
"""Offline pipeline inspector; colors describe implementation, never hardware proof."""
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

NODES=[
 ('entry',420,25,'Parler ou écrire','Premier geste et permission micro','setup','Le navigateur demande un geste et une autorisation pour le micro. La prise est limitée à 15 secondes ; il n’y a pas de mot d’éveil actif.'),
 ('context',420,135,'Contexte figé avant écoute','Dossier · révision · modèle sélectionné','ready','M07 conserve la révision, l’empreinte du contexte et la sélection avant la capture. Une réponse devenue périmée est refusée.'),
 ('memory',800,135,'Mémoire et reprise','Journal · checkpoints · sauvegardes','ready','Les tours, plans et checkpoints occupent la base locale déjà sauvegardée. La restauration neutralise les distributions inachevées.'),
 ('speech',40,245,'Capture puis transcription','Pause locale · modèle STT à configurer','setup','L’arrêt sur pause utilise l’énergie du signal ; il ne comprend pas le sens de la phrase. La chaîne est testée avec un signal synthétique et un faux ASR. Les poids et la qualité réelle restent à qualifier.'),
 ('route',420,355,'LangGraph : route','Ordre déclaré ou interprétation','ready','Le graphe exécuté comporte route, guard, dispatch et receipt. Les ordres connus restent locaux et n’appellent pas Jev.'),
 ('local',40,465,'Règles locales','Dix intentions visuelles déclarées','ready','Une scène de trois vues a été ajoutée au catalogue. Aucune commande système libre ne provient de la transcription.'),
 ('jev',800,465,'Jev facultatif','API distante · clé et essai requis','setup','L’adaptateur utilise Jev 1.14 avec des choix bornés. Jev reçoit le texte, pas le microphone. Sa qualité sur les formulations françaises reste à mesurer.'),
 ('approval',800,575,'Confirmation du choix','Voix explicite ou bouton','ready','« Confirme cet affichage » concerne seulement la proposition visuelle courante de cette fenêtre et de ce dossier. Le contexte est revérifié. « Oui » seul ne suffit pas.'),
 ('guard',420,685,'LangGraph : guard','Contexte · délai · fichiers · annulation','ready','Une demande périmée, annulée ou liée à un modèle incompatible est refusée. L’ensemble de la scène est préparé avant sa première distribution.'),
 ('refuse',40,685,'Refus visible','Aucune réussite inventée','ready','Le message conserve le motif. Un résultat distant inconnu n’est pas répété automatiquement. Une annulation ne promet pas d’effacer un affichage déjà visible.'),
 ('dispatch',420,795,'LangGraph : dispatch','Plan durable · identifiants conservés','ready','La scène produit exactement trois commandes distinctes. Une réponse perdue reprend les mêmes références, y compris après une distribution partielle.'),
 ('journal',800,795,'LangGraph : receipt','Commande en file · état conservé','ready','Ce nœud enregistre la proposition, le refus ou la mise en file. Les reçus de rendu arrivent ensuite de manière asynchrone et sont relus par le suivi des vues.'),
 ('left',40,905,'Gauche · atelier','Planning démonstratif','ready','La vue planning reste explicitement une démonstration. Le parc, ses disponibilités et les temps réels ne sont pas connectés.'),
 ('center',420,905,'Centre · pilotage','Dossiers et opérations','ready','La vue présente les dossiers locaux et les accès au travail conservé. La CAO se crée depuis son circuit de proposition et confirmation existant.'),
 ('right',800,905,'Droite · création','Modèle choisi ou Studio','ready','Le modèle sélectionné est contrôlé puis rendu. Sans sélection explicite, la scène montre le Studio. Aucune sélection de modèle n’est devinée.'),
 ('receipt',420,1015,'Suivi des rendus','Trois accusés · résultat de la scène','ready','Le suivi distingue les vues restantes, affichées ou en échec. La composition complète exige trois reçus. Ils attestent le navigateur, pas le moniteur physique.'),
 ('feedback',420,1125,'Retour à l’utilisateur','État visible · parole locale facultative','setup','La réponse écrite est reliée au résultat. La parole dépend d’une voix française locale du navigateur, à vérifier avec les haut-parleurs réels.'),
]


def diagram():
    positions={n[0]:n for n in NODES};edges=[]
    def add(a,b):
        _,x,y,*_=positions[a];_,xx,yy,*_=positions[b]
        if yy>y:
            start=(x+160,y+76);end=(xx+160,yy);mid=(start[1]+end[1])/2
            d=f'M {start[0]} {start[1]} C {start[0]} {mid} {end[0]} {mid} {end[0]} {end[1]}'
        else:
            start=(x+320 if xx>x else x,y+38);end=(xx if xx>x else xx+320,yy+38);d=f'M {start[0]} {start[1]} L {end[0]} {end[1]}'
        edges.append(f'<path class="edge" d="{d}" marker-end="url(#arrow)"/>')
    for a,b in [('entry','context'),('memory','context'),('context','speech'),('context','route'),('speech','route'),('route','local'),('route','jev'),('jev','approval'),('approval','guard'),('local','guard'),('guard','refuse'),('guard','dispatch'),('dispatch','journal'),('dispatch','left'),('dispatch','center'),('dispatch','right'),('left','receipt'),('center','receipt'),('right','receipt'),('receipt','feedback')]:add(a,b)
    groups=[]
    for ident,x,y,title,detail,state,description in NODES:
        groups.append(f'<g class="node {state}" tabindex="0" role="button" data-node="{ident}" aria-label="{escape(title)}"><rect x="{x}" y="{y}" width="320" height="76" rx="12"/><text x="{x+15}" y="{y+29}" class="title">{escape(title)}</text><text x="{x+15}" y="{y+54}" class="detail">{escape(detail)}</text></g>')
    return '<svg viewBox="0 0 1160 1240" aria-label="Pipeline vocale BOJ.ART M07"><defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#aebac8"/></marker></defs>'+''.join(edges+groups)+'</svg>'


def render():
    target=ROOT/'docs/m07';target.mkdir(parents=True,exist_ok=True)
    data={n[0]:{'title':n[3],'description':n[6],'state':n[5]} for n in NODES}
    html='''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BOJ.ART · Jarvis M07 · Pipeline</title><style>
    :root{color-scheme:dark;--text:#f3f4f9;--muted:#c1c4d2;--accent:#f48fab}*{box-sizing:border-box}body{margin:0;background:#11121a;color:var(--text);font:16px/1.65 system-ui,sans-serif}main{max-width:1240px;margin:auto;padding:40px 25px}h1{font-size:clamp(32px,4vw,55px);line-height:1.1;margin:12px 0 20px;letter-spacing:-1.5px}h2{font-size:25px;margin:24px 0 12px}p{color:var(--muted);max-width:950px}.eyebrow{font-size:12px;letter-spacing:3px;color:var(--accent)}.legend{display:flex;gap:10px;flex-wrap:wrap}.legend span{padding:7px 13px;border:1px solid;border-radius:25px;font-size:13px}.green{color:#8fdfbf}.amber{color:#edbf78}.gray{color:#c2b6d5}figure{margin:20px 0;border:1px solid #3c3b4d;border-radius:16px;background:#1a1923;padding:12px}svg{display:block;width:100%;height:auto}.edge{stroke:#aebac8;stroke-width:2;fill:none}.node{cursor:pointer}.node rect{stroke-width:1.7;transition:stroke-width .15s}.node:focus rect,.node:hover rect{stroke-width:4}.ready rect{fill:#1b3b32;stroke:#73caac}.setup rect{fill:#46341d;stroke:#e9b66b}.title{fill:#fff;font:600 16px system-ui,sans-serif}.detail{fill:#d8d1df;font:13px system-ui,sans-serif}.inspector{position:static;margin:16px 0;border:1px solid #8c546c;border-radius:12px;padding:15px 20px;background:#211923;box-shadow:0 8px 35px #0009}.inspector h2{font-size:19px;margin:0 0 5px}.inspector p{margin:0;font-size:14px}.note{font-size:13px;color:#bec0d0}details{border:1px solid #434152;border-radius:12px;padding:16px;margin:18px 0}summary{cursor:pointer;font-weight:700;color:#f7adc3}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0}.card{border:1px solid #454152;border-radius:12px;padding:16px;background:#201c28}.card h3{margin:0 0 6px;font-size:17px}.card p{margin:0;font-size:14px}.future{border-style:dashed;color:#c4b6d6}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:11px;border-bottom:1px solid #3b384a;text-align:left;vertical-align:top}th{color:#f2a0b8}a{color:#f2a0b8}footer{border-top:1px solid #3b384a;padding-top:24px;margin-top:30px;font-size:13px;color:var(--muted)}@media(max-width:650px){main{padding:24px 14px}.cards{grid-template-columns:1fr}figure{overflow:auto}svg{min-width:850px}.inspector{position:static}table{font-size:12px}td,th{padding:8px}}@media(prefers-reduced-motion:reduce){*{transition:none!important}}
    </style><main><div class="eyebrow">BOJ.ART / M07 / 1 NOVEMBRE 2026</div><h1>Une commande.<br>Trois vues et leurs preuves.</h1><p>« Jarvis, ouvre la tour de contrôle » compose le planning démonstratif, les dossiers et le modèle choisi ou le Studio. Les vues doivent être ouvertes et appairées. Le schéma décrit le logiciel ; la qualification de la tour réelle reste à réaliser.</p><div class="legend"><span class="green">Code exercé localement</span><span class="amber">Configuration ou matériel à qualifier</span><span class="gray">Fonctions futures ci-dessous</span></div><p class="note">Cliquez un bloc pour lire son rôle sous le schéma. Sur mobile, le diagramme peut défiler horizontalement.</p><figure>'''+diagram()+'''</figure><aside class="inspector" aria-live="polite"><h2 id="selectedTitle">Le rôle de chaque brique</h2><p id="selectedDescription">Choisissez un bloc. Le vert décrit des contrôles logiciels ; il ne certifie pas une installation matérielle.</p></aside>
    <details open><summary>La chaîne complète de l’atelier</summary><p>Demande → proposition de conception → confirmation → CAO et fichiers → découpe et profils → planning réel → fabrication FDM/résine → contrôle et finition → médias authentiques → Studio → brouillons → validation → publication → statistiques.</p><div class="cards"><article class="card"><h3>Déjà dans le projet</h3><p>CAO paramétrique depuis le poste dédié, sources et briefs Studio, dossiers, brouillons, affichage, sauvegarde et restauration.</p></article><article class="card"><h3>À configurer et qualifier</h3><p>Poids de transcription, clé Jev, micro, voix française, haut-parleurs et placement des trois moniteurs.</p></article><article class="card future"><h3>À raccorder</h3><p>Découpe, profils et parc réel, imprimantes, rendu vidéo externe, publication et statistiques. Aucun de ces connecteurs n’est activé par ce schéma.</p></article></div></details>
    <details><summary>Les nouvelles données utiles à l’architecture</summary><p>Pipecat fournit un UIWorker et un JevClassifier. Les modules ont été vérifiés dans son paquet 1.15.0 publié ; la pile audio n’est pas installée dans M07. Jev traite le texte et choisit une intention ; il ne remplace pas la reconnaissance ou la synthèse vocale.</p><p>La détection d’une pause ne suffit pas à comprendre la fin d’une pensée. La version actuelle reste une capture par bouton, avec fin manuelle ou sur pause. La conversation continue et le mot d’éveil sont des étapes futures.</p></details>
    <details><summary>Ce qu’il faut mesurer avant le lancement</summary><table><tr><th>Essai</th><th>Preuve attendue</th></tr><tr><td>Voix française et bruit</td><td>Transcriptions, refus, pauses et interruptions sur le vrai microphone</td></tr><tr><td>Trois écrans</td><td>Rendu visible, reçu de chaque vue et reprise après déconnexion</td></tr><tr><td>Jev</td><td>Choix sur les formulations de l’atelier, version fixe et erreurs conservées</td></tr><tr><td>Charge CAO</td><td>Mesures de délai complet, conversation et rendu pendant un calcul</td></tr><tr><td>Sauvegarde</td><td>Restauration dans un nouveau dossier, sans répéter une action en attente</td></tr></table></details>
    <footer>Sources primaires : <a href="https://docs.typesafe.ai/models">TypeSafe / Jev</a> · <a href="https://docs.pipecat.ai/pipecat/learn/ui-worker">Pipecat</a> · <a href="https://www.home-assistant.io/voice_control/voice_remote_local_assistant/">Home Assistant</a> · <a href="https://github.com/leon-ai/leon">Leon</a>. Recherche détaillée, schémas Mermaid et résultats de test dans le paquet M07. Ce document ne charge aucun service externe.</footer></main><script>
    const descriptions='''+json.dumps(data,ensure_ascii=False).replace('</',r'<\/')+''';
    function selectNode(id){const d=descriptions[id];if(!d)return;document.getElementById('selectedTitle').textContent=d.title;document.getElementById('selectedDescription').textContent=d.description;}
    for(const node of document.querySelectorAll('[data-node]')){node.addEventListener('click',()=>selectNode(node.dataset.node));node.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectNode(node.dataset.node);}});}
    </script></html>'''
    (target/'SCHEMA_M07.html').write_text(html,encoding='utf8')
    (target/'CAPACITES_SCHEMA.json').write_text(json.dumps({'version':'M07','observed_date':'2026-11-01','target_hardware_qualified':False,'nodes':data},ensure_ascii=False,indent=2))
    return target/'SCHEMA_M07.html'


if __name__=='__main__':print(render())
