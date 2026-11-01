#!/usr/bin/env python3
import json
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
import analyze_video as module


class AnalysisTests(unittest.TestCase):
    def test_real_cuts_short_event_and_audio_are_distinguished(self):
        with tempfile.TemporaryDirectory(prefix='marwin-video-test-') as tmp:
            root=Path(tmp); rate=48000
            t=np.arange(6*rate)/rate
            sound=np.zeros(len(t))
            sound[(t>=1.5)&(t<1.75)]=.5*np.sin(2*np.pi*1000*t[(t>=1.5)&(t<1.75)])
            with wave.open(str(root/'sound.wav'),'wb') as w:
                w.setparams((1,2,rate,0,'NONE','not compressed'))
                w.writeframes(np.round(sound*32767).astype('<i2').tobytes())
            frames=[]
            for i in range(60):
                c=(220,15,15) if i<20 else ((15,220,15) if i<40 else (15,15,220))
                if i==30:c=(255,255,255)
                image=np.empty((64,96,3),dtype=np.uint8);image[:]=c;frames.append(image.tobytes())
            subprocess.run(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','96x64','-r','10',
                            '-i','-','-i',str(root/'sound.wav'),'-c:v','ffv1','-c:a','pcm_s16le',str(root/'fixture.mkv')],
                           input=b''.join(frames),check=True)
            out=root/'out';out.mkdir()
            result=module.analyze(root/'fixture.mkv',out,threshold=.25,samples=8)
            cuts=[c for c in result['scene_detection']['candidates'] if c['kind']=='cut_or_transition_candidate']
            self.assertTrue(any(abs(c['time_s']-2)<.11 for c in cuts),cuts)
            self.assertTrue(any(abs(c['time_s']-4)<.11 for c in cuts),cuts)
            pairs=result['scene_detection']['short_event_pairs']
            self.assertEqual(len(pairs),1,pairs)
            self.assertAlmostEqual(pairs[0]['start_s'],3,delta=.11)
            events=result['audio']['energy_event_candidates']
            self.assertTrue(any(1.49<=e['time_s']<=1.8 for e in events),events)
            self.assertEqual(result['audio']['transcription']['status'],'not_performed')
            self.assertEqual(result['ocr']['status'],'not_performed')
            self.assertFalse(result['evidence_scope']['viral_effect_proven'])
            self.assertTrue((out/'contact.jpg').is_file())
            self.assertEqual(result['source']['sha256'],module.sha256(root/'fixture.mkv'))
            print(json.dumps({'fixture':'six seconds original','cuts':[x['time_s'] for x in cuts],
                              'short_event':pairs,'audio_events':events},ensure_ascii=False))

    def test_silent_audio_does_not_create_energy_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'silence.wav'
            with wave.open(str(p),'wb') as w:
                w.setparams((2,2,48000,0,'NONE','not compressed'));w.writeframes(bytes(48000*2*2))
            result=module.energy_metrics(p)
            self.assertIsNone(result['sample_peak_dbfs'])
            self.assertIsNone(result['overall_rms_dbfs'])
            self.assertEqual(result['energy_event_candidates'],[])


if __name__=='__main__':
    unittest.main()
