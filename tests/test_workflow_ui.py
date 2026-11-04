"""Browser-to-HTTP integration with a mocked paid model; planning runs for real."""
import importlib.util
import json
from pathlib import Path
import socket
import threading
import time
import unittest
from unittest.mock import patch

import uvicorn
from app import app
from models import ResearchResult


EDGE = Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')
ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(EDGE.is_file() and importlib.util.find_spec('playwright'), 'Edge unavailable')
class WorkflowBrowserTests(unittest.TestCase):
    def test_live_bridge_offline_download_and_key_lifetime(self):
        from playwright.sync_api import sync_playwright
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_level='error'))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        for _ in range(100):
            if server.started:
                break
            time.sleep(.05)
        self.assertTrue(server.started)
        result = ResearchResult.model_validate_json((ROOT / 'sample.json').read_text(encoding='utf-8'))
        result.programmes[0].name = 'Browser integration programme'
        result.warnings = ['Example HTTP 403 access warning']
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path=str(EDGE), headless=True)
                try:
                    page = browser.new_page(viewport={'width':1280,'height':900})
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(f'http://127.0.0.1:{port}/workspace')
                    page.locator('[name=destination]').fill('United Kingdom')
                    page.locator('#run').click()
                    self.assertIn('API Key', page.locator('#status').inner_text())
                    page.locator('#sample').click()
                    page.get_by_role('heading', name='离线流程示例', exact=True).wait_for()
                    self.assertGreater(page.locator('.step').count(), 0)
                    page.locator('#key').fill('browser-test-secret')
                    with patch('app.research', return_value=result) as mock:
                        page.locator('#run').click()
                        page.get_by_role('heading', name='Browser integration programme', exact=True).wait_for()
                        self.assertEqual(mock.call_args.kwargs['api_key'], 'browser-test-secret')
                    self.assertFalse(page.get_by_text('Example HTTP 403 access warning', exact=True).is_visible())
                    self.assertFalse(page.locator('.diagnostics').first.evaluate('(e) => e.open'))
                    page.locator('.diagnostics summary').first.click()
                    self.assertTrue(page.get_by_text('Example HTTP 403 access warning', exact=True).is_visible())
                    page.locator('.diagnostics summary').first.click()
                    self.assertTrue(page.locator('.step details a').first.get_attribute('href').startswith('https://'))
                    with page.expect_download() as download:
                        page.locator('#json').click()
                    content=Path(download.value.path()).read_text(encoding='utf-8')
                    self.assertNotIn('browser-test-secret',content)
                    self.assertTrue(json.loads(content)['plans'][0]['entries'])
                    self.assertEqual(page.evaluate('Object.keys(localStorage)'), ['exchangeprep_language'])
                    self.assertEqual(page.evaluate('Object.keys(sessionStorage)'), [])
                    (ROOT/'tmp').mkdir(exist_ok=True)
                    page.screenshot(path=str(ROOT/'tmp/workflow-desktop.png'),full_page=True)
                    page.set_viewport_size({'width':390,'height':844})
                    self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    page.screenshot(path=str(ROOT/'tmp/workflow-mobile.png'),full_page=True)
                    page.locator('#language-button').click()
                    self.assertEqual(page.locator('html').get_attribute('lang'), 'en')
                    self.assertIn('Your next chapter', page.locator('h1').inner_text())
                    self.assertEqual(page.locator('[name=destination]').input_value(), 'United Kingdom')
                    page.locator('#sample').click()
                    page.get_by_role('heading', name='Offline workflow example', exact=True).wait_for()
                    import re
                    self.assertIsNone(re.search(r'[\u4e00-\u9fff]', page.locator('body').inner_text().replace('中文 ↗','')))
                    self.assertEqual(page.locator('#run').inner_text(), 'Research and build my timeline ↗')
                    page.reload()
                    self.assertEqual(page.locator('#key').input_value(), '')
                    self.assertEqual(errors, [])
                finally:
                    browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=5)
