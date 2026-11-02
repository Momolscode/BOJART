#!/bin/bash
# Montage « Veille — Un seul trait » V1.1 (prête à poster) : 1080x1920, 24 i/s, 12,67 s
# Écarts avec la V1 :
#  - habillage refait dans la zone visible commune (cards_v11.py) ;
#  - mention « Généré par IA » incrustée de la première à la dernière image (AI Act art. 50(4)) ;
#  - accroche « Un seul trait. » visible dès la première image ; carton final ramené de 3 s à 2 s ;
#  - intermédiaires sans perte (la V1 ré-encodait le plan B trois fois en CRF 23) ;
#  - couleurs : calques convertis en BT.709 et fichier étiqueté BT.709 (le carmin du carton
#    dérivait vers l'orange sur téléphone avec la conversion BT.601 par défaut de la V1) ;
#  - encodage aligné sur les recommandations d'import : GOP fermé de 12 images, 2 images B,
#    moov en tête, AAC 48 kHz.
set -e
S=$1; L=$S/lot; B=$S/build; VO=${2:-$L/vo2_celine.mp3}; OUT=$B/BOJART_Veille_UnSeulTrait_V1-1.mp4
FPS=24; CARD=2.0
LOSSLESS="-c:v libx264 -qp 0 -preset ultrafast -pix_fmt yuv420p"
TAGS="-colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv"
# Plans A et B : mêmes coupes et même mouvement que la V1 (YUV conservé, aucune conversion de matrice)
ffmpeg -v error -y -ss 0.875 -i $L/shotA.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=$FPS,format=yuv420p" -t 4.125 -an $LOSSLESS $B/a11.mp4
ffmpeg -v error -y -i $L/shotB.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=$FPS,tpad=start_duration=1.5:start_mode=clone,format=yuv420p" -an $LOSSLESS $B/b11_raw.mp4
NB=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 $B/b11_raw.mp4)
ffmpeg -v error -y -i $B/b11_raw.mp4 -vf "scale=2160:3840,zoompan=z='1.14+0.10*on/$NB':x='iw/2-(iw/zoom/2)':y='ih*0.42-(ih/zoom*0.42)':d=1:s=1080x1920:fps=$FPS,format=yuv420p" $LOSSLESS $B/b11.mp4
# Carton : 2 s, fondu d'entrée 0,4 s, conversion RGB -> YUV en BT.709
ffmpeg -v error -y -loop 1 -i $B/v11_endcard.png -vf "fps=$FPS,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,fade=in:st=0:d=0.4" -t $CARD $LOSSLESS $B/c11.mp4
DA=4.125; DB=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $B/b11.mp4)
TB=$(python3 -c "print($DA+$DB)"); TOT=$(python3 -c "print($DA+$DB+$CARD)")
echo "NB=$NB B=$DB carton@$TB total=$TOT"
# Assemblage + habillage en un seul encodage final : mention permanente, accroche dès 0 s, phrase 2 calée sur le regard
C1A=0; C1B=3.8; C2A=$(python3 -c "print($DA+2.4)"); C2B=$(python3 -c "print($DA+$DB-0.2)")
OV="scale=out_color_matrix=bt709:out_range=tv,format=yuva420p"
ffmpeg -v error -y -i $B/a11.mp4 -i $B/b11.mp4 -i $B/c11.mp4 -i $B/v11_mention.png -i $B/v11_cap1.png -i $B/v11_cap2.png -filter_complex \
 "[0][1][2]concat=n=3:v=1:a=0,format=yuv420p[cat];[3]$OV[m];[4]$OV[c1];[5]$OV[c2];[cat][m]overlay[v1];[v1][c1]overlay=enable='between(t,$C1A,$C1B)'[v2];[v2][c2]overlay=enable='between(t,$C2A,$C2B)',format=yuv420p[v]" \
 -map "[v]" -c:v libx264 -preset slow -crf 16 -profile:v high -level:v 4.1 -pix_fmt yuv420p \
 -g 12 -keyint_min 12 -bf 2 -x264-params open-gop=0 -maxrate 20M -bufsize 40M $TAGS -r $FPS $B/v11_video.mp4
# Son : bed synthétisé + voix (phrase 1 à 0,75 s ; phrase 2 calée sur le regard), −14 LUFS
python3 $B/sound.py $B/bed11.wav "{\"total\": $TOT, \"brush\": [[0.05, 3.5]], \"swell\": [$DA, $(python3 -c "print($DA+2.6)")], \"hit\": $TB}"
ffmpeg -v error -y -i $VO -af "atrim=0:1.32,asetpts=PTS-STARTPTS" -ar 48000 $B/vo1.wav
ffmpeg -v error -y -i $VO -af "atrim=start=1.60,asetpts=PTS-STARTPTS" -ar 48000 $B/vo2.wav
D1=750; D2=$(python3 -c "print(int(($DA+2.5)*1000))")
ffmpeg -v error -y -i $B/bed11.wav -i $B/vo1.wav -i $B/vo2.wav -filter_complex "[1]adelay=$D1|$D1[a1];[2]adelay=$D2|$D2[a2];[0]volume=0.55[bed];[bed][a1][a2]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=7[a]" -map "[a]" -ar 48000 -c:a pcm_s16le $B/mix11.wav
ffmpeg -v error -y -i $B/v11_video.mp4 -i $B/mix11.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart $OUT
echo done $OUT
