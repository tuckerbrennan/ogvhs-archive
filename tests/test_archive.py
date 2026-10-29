import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def load_file(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/f'{name}.py')
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

b=load_file('build')
i=load_file('import_vines')

class ArchiveTests(unittest.TestCase):
    def test_id_inference(self):
        self.assertEqual(i.infer_id('50W0x3Pu6xJ.mp4'),'50W0x3Pu6xJ')
        self.assertEqual(i.infer_id('50W0x3Pu6xJ.sub.mp4'),'50W0x3Pu6xJ')
        self.assertEqual(i.infer_id('vine_50W0x3Pu6xJ (1).mp4'),'50W0x3Pu6xJ')
        for name in ['._50W0x3Pu6xJ.mp4','.DS_Store','5aZbBALIjFu.jpeg','not-an-id.mp4']:
            self.assertIsNone(i.infer_id(name),name)

    def test_hashtags_are_deduplicated(self):
        self.assertEqual(b.tags_for('Look at this #Wow #wow #Jersey', ['#WOW','Extra']),['wow','jersey','extra'])
        markup=b.caption_html('Look at <tag> #Vine #Vine')
        self.assertIn('&lt;tag&gt;',markup)
        self.assertIn('tag/vine/',markup)
        self.assertNotIn('<tag>',markup)

    def test_metadata_merge_does_not_erase_existing(self):
        starting=[{'vineId':'50W0x3Pu6xJ','rawCaption':'Original #Jersey','publishedAt':'2015-01-01','videoUrl':'https://cdn.example.org/a.mp4'}]
        rows=[{'vineId':'50W0x3Pu6xJ','caption':'','publishedAt':'','videoUrl':''},{'vineId':'5aZbBALIjFu','caption':'Recovered #Test','date':'2016-02-02'}]
        merged,rep=i.merge(starting,[],rows)
        by={r['vineId']:r for r in merged}
        self.assertEqual(by['50W0x3Pu6xJ']['rawCaption'],'Original #Jersey')
        self.assertEqual(by['50W0x3Pu6xJ']['videoUrl'],'https://cdn.example.org/a.mp4')
        self.assertEqual(by['5aZbBALIjFu']['publishedAt'],'2016-02-02')
        self.assertEqual(rep['metadata_new_rows'],1)

    def test_date_normalization(self):
        self.assertEqual(i.normalize_date('2014-03-02'),'2014-03-02')
        self.assertEqual(i.normalize_date('1400000000'),'2014-05-13T16:53:20Z')

    def test_playable_clip_loops_by_default_and_can_be_toggled(self):
        v = {'vineId': '50W0x3Pu6xJ', 'videoUrl': '/ogvhs-archive/media/example.mp4',
             'thumbnailUrl': None, 'rawCaption': None, 'tags': [],
             'publishedAt': None, 'dateLabel': 'Date unknown',
             'idKind': 'vine', 'sourceFilename': 'example.mp4'}
        markup = b.detail_page(v)
        self.assertIn('<video id="vine-player" controls loop playsinline', markup)
        self.assertIn('id="toggle-loop" type="button" aria-pressed="true">LOOP ON ↻', markup)
        js = (ROOT / 'assets/app.js').read_text(encoding='utf-8')
        self.assertIn('video.loop = !video.loop;', js)
        self.assertIn("loop.textContent = video.loop ? 'LOOP ON ↻' : 'LOOP OFF';", js)

    def test_vault_branding_and_hover_audio(self):
        markup=b.home([], {})
        self.assertIn('In the<br>vault.',markup)
        self.assertNotIn('Every clip has an ID.',markup)
        self.assertNotIn('FIND IT',markup)
        self.assertIn('A NOTE FROM THE VAULT', markup)
        vmarkup=b.browser([])
        self.assertIn('THE VAULT.',vmarkup)
        js=(ROOT/'assets/app.js').read_text(encoding='utf-8')
        self.assertIn('video.muted = false;',js)
        self.assertIn('ENABLE SOUND',js)
        self.assertIn('video.loop = true;',js)

    def test_build_generates_shareable_staging_and_production_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            oldroot,olddist,oldenv,oldbase,oldsite=b.ROOT,b.DIST,b.ENV,b.BASE_PATH,b.SITE_URL
            root=Path(temp)
            (root/'data').mkdir()
            (root/'assets').mkdir()
            (root/'data/vines.json').write_text(json.dumps([
                {'vineId':'50W0x3Pu6xJ','rawCaption':'Test caption #Great','publishedAt':'2015-01-01','videoUrl':'https://cdn.example.org/test.mp4'},
                {'vineId':'5aZbBALIjFu','rawCaption':None,'publishedAt':None}
            ]))
            (root/'assets/test.css').write_text('body{}')
            try:
                b.ROOT=root;b.DIST=root/'dist';b.ENV='staging';b.BASE_PATH='/ogvhs-archive/';b.SITE_URL='https://tuckerbrennan.github.io'
                b.build()
                self.assertTrue((root/'dist/v/50W0x3Pu6xJ/index.html').exists())
                self.assertTrue((root/'dist/tag/great/index.html').exists())
                staging=(root/'dist/v/50W0x3Pu6xJ/index.html').read_text()
                self.assertIn('/ogvhs-archive/tag/great/',staging)
                self.assertIn('noindex',staging)
                self.assertFalse((root/'dist/CNAME').exists())
                b.ENV='production';b.BASE_PATH='/';b.SITE_URL='https://ogvhs.com'
                b.build()
                prod=(root/'dist/v/50W0x3Pu6xJ/index.html').read_text()
                self.assertIn('https://ogvhs.com/v/50W0x3Pu6xJ/',prod)
                self.assertIn('href="/tag/great/"',prod)
                self.assertNotIn('/ogvhs-archive/',prod)
                self.assertEqual((root/'dist/CNAME').read_text(),'ogvhs.com\n')
                self.assertTrue((root/'dist/sitemap.xml').exists())
            finally:
                b.ROOT=oldroot;b.DIST=olddist;b.ENV=oldenv;b.BASE_PATH=oldbase;b.SITE_URL=oldsite

if __name__=='__main__':unittest.main()
