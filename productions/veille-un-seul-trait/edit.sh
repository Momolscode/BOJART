#!/bin/bash
# Montage « Veille — Un seul trait » V1 : 1080x1920, 24 i/s, ~14,5 s
set -e
S=$1; L=$S/lot; B=$S/build; VO=${2:-$L/vo2_celine.mp3}; OUT=$B/BOJART_Veille_UnSeulTrait_V1.mp4
FPS=24
# Plan A : le trait (5 s)
ffmpeg -v error -y -ss 0.875 -i $L/shotA.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=$FPS,format=yuv420p" -t 4.125 -an $B/a.mp4
# Plan B : 1,5 s de pose (image 1 tenue) + 5 s de clip, poussée lente continue 1.00 -> 1.06
ffmpeg -v error -y -i $L/shotB.mp4 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=$FPS,tpad=start_duration=1.5:start_mode=clone,format=yuv420p" -an $B/b_raw.mp4
NB=$(ffprobe -v error -count_frames -select_streams v -show_entries stream=nb_read_frames -of csv=p=0 $B/b_raw.mp4)
ffmpeg -v error -y -i $B/b_raw.mp4 -vf "scale=2160:3840,zoompan=z='1.14+0.10*on/$NB':x='iw/2-(iw/zoom/2)':y='ih*0.42-(ih/zoom*0.42)':d=1:s=1080x1920:fps=$FPS,format=yuv420p" $B/b.mp4
# Carton : 3 s, fondu d'entrée
ffmpeg -v error -y -loop 1 -i $B/endcard.png -vf "fps=$FPS,format=yuv420p,fade=in:st=0:d=0.6" -t 3 $B/c.mp4
# Assemblage + sous-titres
DA=4.125; DB=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $B/b.mp4)
TB=$(python3 -c "print($DA+$DB)"); TOT=$(python3 -c "print($DA+$DB+3)")
echo "B=$DB carton@$TB total=$TOT"
printf "file '%s'\nfile '%s'\nfile '%s'\n" $B/a.mp4 $B/b.mp4 $B/c.mp4 > $B/list.txt
ffmpeg -v error -y -f concat -safe 0 -i $B/list.txt -c copy $B/v_cat.mp4
C1A=0.7; C1B=3.8; C2A=$(python3 -c "print($DA+2.4)"); C2B=$(python3 -c "print($DA+$DB-0.2)")
ffmpeg -v error -y -i $B/v_cat.mp4 -i $B/cap1.png -i $B/cap2.png -filter_complex "[0][1]overlay=enable='between(t,$C1A,$C1B)'[v1];[v1][2]overlay=enable='between(t,$C2A,$C2B)'[v]" -map "[v]" -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -r $FPS $B/v_final.mp4
# Son : bed synthétisé + voix (phrase 1 à 1,2 s ; phrase 2 calée sur le regard)
python3 $B/sound.py $B/bed.wav "{\"total\": $TOT, \"brush\": [[0.05, 3.5]], \"swell\": [$DA, $(python3 -c "print($DA+2.6)")], \"hit\": $TB}"
ffmpeg -v error -y -i $VO -af "atrim=0:1.32,asetpts=PTS-STARTPTS" -ar 48000 $B/vo1.wav
ffmpeg -v error -y -i $VO -af "atrim=start=1.60,asetpts=PTS-STARTPTS" -ar 48000 $B/vo2.wav
D1=750; D2=$(python3 -c "print(int(($DA+2.5)*1000))")
ffmpeg -v error -y -i $B/bed.wav -i $B/vo1.wav -i $B/vo2.wav -filter_complex "[1]adelay=$D1|$D1,volume=1.0[a1];[2]adelay=$D2|$D2,volume=1.0[a2];[0]volume=0.55[bed];[bed][a1][a2]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=7[a]" -map "[a]" -ar 48000 -c:a pcm_s16le $B/mix.wav
ffmpeg -v error -y -i $B/v_final.mp4 -i $B/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart $OUT
echo done $OUT
