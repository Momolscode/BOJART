"""Explicit, local seed from three already supplied project media files.
Intervals below are human editorial annotations, not an AI video analysis.
"""
from pathlib import Path
from core import Rejected

def seed(library,root):
 root=Path(root)
 aid=library.ingest(root/'source_bojart.mp4','Vidéo BOJ.ART transmise · montage TikTok','user_upload',
   'Pièce jointe v24044gl0000cuei73fog65q7gjmvfc0.mp4. Copie déjà montée : logo, animation et vraie sculpture ; pas un rush brut certifié.')
 bid=library.ingest(root/'animatique_v4.mp4','Animatique V4 · images fixes animées','assistant_render',
   'Ancien livrable BOJART_BREAK_THE_FRAME_V4_ANIMATIC_TEST.mp4. Mouvement de caméra sur des cases conceptuelles ; pas une captation de la figurine.')
 cid=library.ingest(root/'essai_vfx_2d.mp4','Essai de rupture · compositing 2D','assistant_render',
   'Ancien livrable BOJART_VFX_BREAK_FRAME_PROOF.mp4 ; illustration de principe issue du storyboard. Aucun personnage réel photographié dans ce fichier.')
 records=[
 ('intro',aid,'Introduction logo + animation',0.0,3.8,'mixed','unreviewed',False,['logo','anime','introduction'],'Images de contrôle à 0,6 et 2,8 s : illustration et extrait animé ; ne pas en déduire le modèle de sculpture.'),
 ('profil',aid,'Sculpture · profil et socle',5.0,6.0,'authentic_capture','approved_internal',True,['sculpture','profil','socle','vraie figurine'],'Comparaison visuelle des images extraites du média fourni. Validation interne de catégorie, pas validation technique ni droits.'),
 ('ensemble',aid,'Sculpture · vue d’ensemble',6.6,7.5,'authentic_capture','approved_internal',True,['sculpture','ensemble','corps','socle'],'Passage court de la pièce réelle ; contrôle visuel échantillonné pour repérer le sujet.'),
 ('troisquarts',aid,'Sculpture · trois-quarts',8.5,9.4,'authentic_capture','approved_internal',True,['sculpture','reference','short bordeaux','trois quarts'],'Vue originale déjà retenue dans la fiche de fidélité V6. Source vidéo conservée par empreinte.'),
 ('visage',aid,'Sculpture · visage et tenue',10.2,11.1,'authentic_capture','approved_internal',True,['sculpture','visage','reference','short bordeaux','cicatrices'],'Vue originale à 10,2 s du dossier V6. Sert à comparer le personnage ; ne prouve aucune dimension physique.'),
 ('outro',aid,'Outro · illustration et promotion',12.8,15.1,'mixed','unreviewed',False,['logo','outro','promotion'],'Fin montée du clip ; informations promotionnelles anciennes, non reprises comme offre actuelle.'),
 ('concept-v4',bid,'V4 · intention de combat',0.0,min(4.0,library.asset(bid)['metadata']['duration']),'concept','unreviewed',False,['storyboard','combat','concept'],'Illustration d’intention seulement ; exclue du rôle référence authentique.'),
 ('vfx-2d',cid,'Rupture 2D · hors référence personnage',0.0,min(4.0,library.asset(cid)['metadata']['duration']),'concept','rejected',False,['verre','rupture','essai'],'Décision de ce pilote : exclu des références de personnage car fondé sur une illustration, pas sur la vraie sculpture. Ce n’est pas un nouveau verdict utilisateur.')
 ]
 for sid,a,label,st,en,kind,review,anchor,tags,evidence in records:
  try:library.segment(sid)
  except Rejected:library.annotate(sid,a,label,st,en,kind,review,identity_anchor=anchor,evidence=evidence,tags=tags)
 return library.catalogue()
