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


if __name__=='__main__':
    unittest.main()
