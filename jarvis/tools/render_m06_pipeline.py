#!/usr/bin/env python3
"""Generate the standalone, offline engineering diagram (no external scripts)."""
from html import escape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def render():
    nodes=[
        ('input',420,25,'Commande de l’utilisateur','Texte ou bouton « Parler »','ready'),
        ('asr',420,135,'Transcription locale','Voix : modèle et micro à qualifier','setup'),
        ('turn',420,245,'Tour et contexte figés','Dossier · révision · modèle sélectionné','ready'),
        ('memory',40,245,'Mémoire persistante','Journal · checkpoints · sauvegardes','ready'),
        ('route',420,355,'LangGraph : routage','Ordre connu ou interprétation facultative','ready'),
        ('local',40,465,'Commandes locales','9 intentions visuelles déclarées','ready'),
        ('jev',800,465,'Jev : choix parmi le catalogue','Adaptateur prêt · clé et essai manquants','setup'),
        ('confirm',800,575,'Proposition de Jev','Confirmer ou reformuler','setup'),
        ('guard',420,685,'Contrôles avant distribution','Révision · délai · annulation · fichiers','ready'),
        ('stop',40,685,'Refus explicite','Contexte périmé, doute ou annulation','ready'),
        ('dispatch',420,795,'Distribution durable','Signal immédiat + repli périodique','ready'),
        ('modules',40,905,'Contenu des vues','CAO · Studio · dossiers · base · contenus','ready'),
        ('views',420,905,'Trois vues de navigateur','Atelier · pilotage · création','ready'),
        ('future',800,905,'Raccordements futurs','Machines · vidéo · publication · métriques','future'),
        ('ack',420,1015,'Reçu après rendu','Preuve logicielle ; matériel à qualifier','ready'),
        ('feedback',800,1015,'Réponse et continuité','État visible · TTS local facultatif','setup'),
    ]
    boxes={n[0]:n for n in nodes};paths=[]
    def edge(a,b,kind='',label=''):
        _,x,y,*_=boxes[a];_,xx,yy,*_=boxes[b]
        if yy>y:
            x1,y1=x+160,y+76;x2,y2=xx+160,yy
            d=f'M {x1} {y1} C {x1} {(y1+y2)/2} {x2} {(y1+y2)/2} {x2} {y2}'
        else:
            x1,y1=(x+320 if xx>x else x),y+38;x2,y2=(xx if xx>x else xx+320),yy+38
            d=f'M {x1} {y1} L {x2} {y2}'
        paths.append(f'<path d="{d}" class="edge {kind}" marker-end="url(#arrow)"/>')
    for a,b in [('input','asr'),('asr','turn'),('memory','turn'),('turn','route'),('route','local'),('route','jev'),('jev','confirm'),('local','guard'),('confirm','guard'),('guard','stop'),('guard','dispatch'),('dispatch','views'),('modules','views'),('views','ack'),('ack','feedback')]:edge(a,b)
    edge('views','future','planned')
    # The typed path does not require speech recognition.
    paths.append('<path d="M 740 63 H 765 V 283 H 740" class="edge" marker-end="url(#arrow)"/><text x="775" y="200" class="edgeLabel">texte</text>')
    groups=[]
    for ident,x,y,title,detail,kind in nodes:
        groups.append(f'<g class="node {kind}"><rect x="{x}" y="{y}" width="320" height="76" rx="12"/><text x="{x+16}" y="{y+29}" class="title">{escape(title)}</text><text x="{x+16}" y="{y+54}" class="detail">{escape(detail)}</text></g>')
    svg='<svg viewBox="0 0 1160 1120" role="img" aria-labelledby="diagramTitle diagramDesc"><title id="diagramTitle">Pipeline BOJ.ART Jarvis M06</title><desc id="diagramDesc">Commande voix ou texte, contexte, LangGraph, règles locales ou Jev, contrôle, distribution aux vues puis accusé. Mémoire et sauvegardes persistantes. Adaptateurs physiques futurs.</desc><defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8" fill="#b3b5c8"/></marker></defs>'+''.join(paths+groups)+'</svg>'
    html='''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BOJ.ART · Jarvis M06 · Pipeline</title><style>
    :root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#111119;color:#f3f0f6;font:16px/1.65 system-ui,sans-serif}main{max-width:1220px;margin:auto;padding:40px 24px}h1{font-size:clamp(30px,4vw,54px);line-height:1.1;letter-spacing:-1.5px;margin:12px 0 20px}h2{font-size:24px;margin:28px 0 12px}p{color:#c6bfd0;max-width:900px}.eyebrow{color:#f785a0;font-size:12px;letter-spacing:3px}.legend{display:flex;gap:12px;flex-wrap:wrap}.legend span{padding:8px 14px;border:1px solid;border-radius:24px;font-size:13px}.ok{color:#93e8cb}.maybe{color:#f2c772}.later{color:#c7b9dc}figure{margin:25px 0;border:1px solid #393447;background:#191720;border-radius:18px;padding:14px}svg{display:block;width:100%;height:auto}.edge{fill:none;stroke:#b3b5c8;stroke-width:2}.planned{stroke-dasharray:7 6}.node rect{stroke-width:1.6}.ready rect{fill:#19382f;stroke:#68c8ac}.setup rect{fill:#3b2d17;stroke:#e4b566}.future rect{fill:#302a38;stroke:#a791bd;stroke-dasharray:7 5}.title{fill:#fcfaff;font:600 16px system-ui,sans-serif}.detail{fill:#d1cbd6;font:13px system-ui,sans-serif}.edgeLabel{fill:#c6bfd0;font:13px system-ui}figcaption{font-size:13px;color:#b7aec6;margin:10px}table{width:100%;border-collapse:collapse;font-size:14px}td,th{border-bottom:1px solid #383243;text-align:left;padding:12px;vertical-align:top}th{color:#f09bb0}a{color:#f4a8bd}details{border:1px solid #494052;padding:16px;border-radius:12px;margin:16px 0}summary{cursor:pointer;font-weight:700}footer{border-top:1px solid #423748;padding-top:24px;margin-top:30px;color:#bdb2c9;font-size:13px}@media(max-width:650px){main{padding:24px 14px}figure{overflow:auto;padding:8px}svg{min-width:850px}table{font-size:12px}td,th{padding:8px}}
    </style><main><div class="eyebrow">BOJ.ART / 31 OCTOBRE 2026</div><h1>Un ordre. Un contexte.<br>Un résultat vérifié.</h1><p>Pipeline de Jarvis M06. Le vert décrit du code exercé localement. L’orange exige une configuration ou une qualification réelle. Les pointillés décrivent des raccordements futurs.</p><div class="legend"><span class="ok">Code local testé</span><span class="maybe">Configuration / qualification</span><span class="later">À raccorder</span></div><figure>'''+svg+'''<figcaption>Sur mobile, faire défiler le schéma horizontalement. Les fichiers Mermaid éditables sont inclus dans le paquet.</figcaption></figure>
    <h2>Ce qui apparaît dans les vues</h2><table><thead><tr><th>Commande</th><th>Résultat</th><th>Limite</th></tr></thead><tbody><tr><td>Affiche le modèle à droite</td><td>Modèle conservé, contrôlé et rendu</td><td>Sélection explicite du modèle</td></tr><tr><td>Montre les dossiers au centre</td><td>Dossiers, compteurs et accès aux sauvegardes</td><td>Données locales</td></tr><tr><td>Ouvre le studio</td><td>Catalogue des sources à droite</td><td>Catalogue partagé</td></tr><tr><td>Ouvre les contenus à droite</td><td>État des préparations éditoriales</td><td>Aucune publication externe</td></tr><tr><td>Ouvre la base métier au centre</td><td>Accès à la recherche documentaire</td><td>Mots-clés et sources</td></tr><tr><td>Ouvre la conception au centre</td><td>Accès au poste CAO du dossier</td><td>Calcul soumis à proposition et confirmation</td></tr><tr><td>Affiche le planning à gauche</td><td>Vue de planning démonstrative</td><td>Parc réel non connecté</td></tr></tbody></table>
    <details open><summary>La position de Jev</summary><p>Jev intervient après le texte final pour choisir une intention dans un catalogue. Il ne transcrit pas le microphone et ne parle pas. Les règles locales suffisent aux ordres connus. Sa proposition reste soumise à confirmation et aux contrôles de contexte ; aucun appel réel à Jev n’a été effectué dans cette recette.</p></details>
    <details><summary>La voix et les performances</summary><p>La capture est reliée à la chaîne de commandes, avec un propriétaire audio unique et une prise de 15 secondes maximum. Les tests de bout en bout emploient un microphone synthétique et un faux transcripteur explicitement identifiés. Le vrai micro, les poids de reconnaissance et la voix de retour restent à qualifier.</p><p>La dernière série de douze commandes au calme va de 66 à 98 ms entre l’envoi du texte et le reçu du navigateur. Sous calcul CAO réel, six commandes restent utilisables et aboutissent en 115 à 997 ms avant la fin du calcul. Une autre passe présentait un pic de 1,4 seconde. Ces petits essais excluent ASR et Jev ; la latence de la tour réelle reste à mesurer. La conversation continue avec Pipecat/SmallWebRTC reste une étape future.</p></details>
    <details><summary>Atelier complet : ce qui reste à raccorder</summary><p>Demande → proposition CAO → validation → fichiers et aperçu → découpe et profils → planning réel → imprimante FDM/résine → contrôle physique → médias authentiques → Studio → brouillon → validation → publication → statistiques. Les étapes physiques, le rendu externe, la publication et les métriques ne sont pas actives dans M06.</p></details>
    <footer>Sources : <a href="https://docs.typesafe.ai/models">TypeSafe / Jev</a> · <a href="https://docs.langchain.com/oss/python/langgraph/persistence">LangGraph</a> · <a href="https://www.home-assistant.io/voice_control/voice_remote_local_assistant/">Home Assistant</a> · <a href="https://docs.pipecat.ai/client/concepts/choosing-a-transport">Pipecat</a>. Recherche détaillée et instructions de reprise dans le paquet M06. Aucun service externe n’est chargé par ce document.</footer></main></html>'''
    target=ROOT/'docs/m06/SCHEMA_M06.html';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(html,encoding='utf8')
    return target


if __name__=='__main__':print(render())
