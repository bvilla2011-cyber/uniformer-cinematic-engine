import json
import unittest
from pathlib import Path
from engine.studio import Studio, validate_project

PROJECT = Path(__file__).resolve().parents[1] / 'projects' / 'first_light.json'

class TestStudio(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(PROJECT.read_text(encoding='utf-8'))

    def test_duration(self):
        self.assertAlmostEqual(validate_project(self.data), 10.0)

    def test_reject_untrusted_scene(self):
        self.data['shots'][0]['type'] = 'execute_python'
        with self.assertRaises(ValueError):
            validate_project(self.data)

    def test_reject_oversized_project(self):
        self.data['shots'] *= 5
        with self.assertRaises(ValueError):
            validate_project(self.data)

    def test_distinct_frames(self):
        engine = Studio(self.data,270,480)
        a = engine.render_at(.1)
        b = engine.render_at(1.9)
        self.assertEqual(a.size,(270,480))
        self.assertNotEqual(a.tobytes(),b.tobytes())

    def test_each_scene(self):
        engine = Studio(self.data,270,480)
        for t in (.5,3.8,7.3):
            self.assertEqual(engine.render_at(t).size,(270,480))


class TestBrief(unittest.TestCase):
    def test_model_json_validated(self):
        from engine.brief import parse_response
        data = json.loads(PROJECT.read_text(encoding='utf-8'))
        self.assertEqual(parse_response(json.dumps(data))['title'], data['title'])

    def test_model_code_rejected(self):
        from engine.brief import parse_response
        with self.assertRaises(ValueError):
            parse_response('{"title":"bad","shots":[{"type":"run_code","duration":1}]}')

    def test_insecure_endpoint_rejected(self):
        from engine.brief import generate
        with self.assertRaises(ValueError):
            generate('An original ad',endpoint='http://example.com/v1/chat/completions',model='test')



class TestCaptions(unittest.TestCase):
    def test_timed_caption_and_logo(self):
        from PIL import Image
        from tempfile import TemporaryDirectory
        data = json.loads(PROJECT.read_text(encoding='utf-8'))
        data['captions'] = [{'start': 1.0, 'end': 2.0, 'text': 'THE NEXT WORLD'}]
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'brand.png'
            Image.new('RGBA', (50, 30), (250, 250, 250, 200)).save(path)
            engine = Studio(data,270,480,logo_path=path)
            self.assertNotEqual(engine.render_at(1.5).tobytes(), engine.render_at(2.1).tobytes())
            self.assertEqual(engine.render_at(8.0).size, (270,480))

    def test_reject_caption_outside_duration(self):
        data = json.loads(PROJECT.read_text(encoding='utf-8'))
        data['captions'] = [{'start': 11, 'end': 12, 'text': 'Invalid'}]
        with self.assertRaises(ValueError):
            validate_project(data)

if __name__=='__main__':
    unittest.main()
