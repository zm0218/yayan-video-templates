"""HT视频001 public inputs and portable assets; never requests online speech."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared.runtime import select_template, verify_assets
T = ROOT/'templates/whitening/ht-video-001'
spec = importlib.util.spec_from_file_location('ht_video_001', T/'make.py')
ht = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ht)


class HTContractTests(unittest.TestCase):
    def test_template_registration_and_assets(self):
        item, folder = select_template('ht-video-001')
        self.assertEqual(item['name'], 'HT视频001')
        self.assertEqual(folder, T)
        self.assertEqual(item['outputPattern'], 'HiTeeth皓得适-合作视频-{clinic_name}.mp4')
        self.assertGreater(len(verify_assets(T)['files']), 30)
        self.assertIn('SIL OPEN FONT LICENSE', (T/'assets/fonts/OFL.txt').read_text(encoding='utf-8'))

    def test_personalized_voice_not_distributed(self):
        job = json.loads((T/'template.json').read_text(encoding='utf-8'))
        self.assertEqual(len(job['scenes']), 9)
        for scene in job['scenes']:
            personal = '{{clinic_name}}' in scene['text']
            for ext in ('.mp3', '.txt', '.jsonl'):
                self.assertEqual((T/'audio-cache'/(scene['id']+ext)).exists(), not personal)
        for file in (T/'audio-cache').glob('*.txt'):
            self.assertNotIn('{{clinic_name}}', file.read_text(encoding='utf-8'))

    def test_explicit_voice_permission_and_offline_preview(self):
        cmd = [sys.executable, str(ROOT/'video.py'), '--template', 'ht-video-001', '--name', '测试口腔', '--logo', 'missing.png']
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--allow-online-tts', result.stderr)
        preview = subprocess.run([*cmd, '--preview'], capture_output=True, text=True, encoding='utf-8')
        self.assertIn('Logo 文件不存在', preview.stderr)
        self.assertNotIn('本模板使用在线语音', preview.stderr)

    def test_clinic_names_remain_exact_and_safe(self):
        for name in ('瑞华口腔', 'A&B 口腔', '美白模板验证口腔'):
            self.assertEqual(ht.validate_name(name), name)
            self.assertEqual(ht.substitute({'text':'{{clinic_name}}携手皓得适'}, name, 'logo.svg')['text'], name+'携手皓得适')
        for name in ('', '../诊所', '诊所:分院', '诊所\\分院', '{{clinic_name}}', '诊所.'):
            with self.assertRaises(ValueError):
                ht.validate_name(name)


if __name__ == '__main__':
    unittest.main()
