"""Public-release and user-facing invariants; no TTS or external network."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from shared.runtime import load_catalog, select_template, verify_assets
T=ROOT/'templates/orthodontics/ds-a'
spec=importlib.util.spec_from_file_location('ds_a',T/'make.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ContractTests(unittest.TestCase):
    def test_catalog_routes_and_filenames(self):
        ids=[]
        for item in load_catalog()['templates']:
            ids.append(item['id'])
            _,folder=select_template(item['id'])
            self.assertTrue((folder/item['entry']).is_file())
            self.assertTrue(item['outputPattern'].endswith('-{clinic_name}.mp4'))
        self.assertEqual(len(ids),len(set(ids)))

    def test_no_private_paths_or_credentials_in_public_text(self):
        for root in ['shared','scripts','tests','docs','templates']:
            for path in (ROOT/root).rglob('*'):
                if path.suffix not in ['.py','.cjs','.json','.md','.svg']:continue
                text=path.read_text(encoding='utf-8')
                # Assemble patterns so the scanner does not match its own source.
                for forbidden in ['/'+'Users/', 'C:'+'\\Users\\', 'gh'+'p_', 'BEGIN '+'PRIVATE KEY']:
                    self.assertNotIn(forbidden,text,str(path.relative_to(ROOT)))

    def test_offline_preview_does_not_require_voice_consent(self):
        args=[sys.executable,str(ROOT/'video.py'),'--template','ds-a','--name','测试口腔','--logo','does-not-exist.png']
        no_consent=subprocess.run(args,capture_output=True,text=True,encoding='utf-8')
        self.assertNotEqual(no_consent.returncode,0)
        self.assertIn('--allow-online-tts',no_consent.stderr)
        preview=subprocess.run([*args,'--preview'],capture_output=True,text=True,encoding='utf-8')
        self.assertIn('Logo 文件不存在',preview.stderr)
        self.assertNotIn('本模板使用在线语音',preview.stderr)

    def test_cross_platform_name_boundary(self):
        for name in ['瑞华口腔','A&B 口腔','昱宏口腔','长名称数字化诊疗中心联合门诊']:
            self.assertEqual(module.validate_name(name),name)
        for name in ['','../其他目录','口腔:中心','口腔\\中心','口腔\n诊所','{{clinic_name}}','诊所.']:
            with self.assertRaises(ValueError):module.validate_name(name)

    def test_voice_and_display_are_separate(self):
        scenes=json.loads((T/'story.template.json').read_text(encoding='utf-8'))
        self.assertEqual(sum(s['personalizedVoice'] for s in scenes),3)
        self.assertEqual(len(scenes),8)
        for scene in scenes:
            if not scene['personalizedVoice']:
                self.assertNotIn('{{clinic_name}}',scene['text'])
        self.assertEqual(module.substitute({'text':'{{clinic_name}}，正畸。'},'A&B 口腔')['text'],'A&B 口腔，正畸。')

    def test_asset_hashes_and_font_license(self):
        self.assertGreaterEqual(len(verify_assets(T)['files']),14)
        self.assertIn('SIL OPEN FONT LICENSE',(T/'assets/fonts/OFL.txt').read_text())


if __name__=='__main__':unittest.main()
