"""End-to-end tests for the gold and silver edition, on synthetic data (not real prices).

    python3 -m unittest discover -s tests -v

make_fixtures.py writes 60+ sessions of 5-minute GC=F / SI=F bars with a planted
opening-range breakout on Fri 2026-11-13 (range 12:00-12:15 Dubai), then each test
runs the real command-line tools against them in a temporary folder.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = {
    "scan": "trader-scanner/scan.py", "news": "trader-news/news.py", "entry": "trader-entry/entry.py",
    "exit": "trader-exit/exit.py", "tm": "trader-timemachine/timemachine.py", "size": "trader-budget/size.py",
    "risk": "trader-risk/check.py", "alerts": "trader-alerts/alerts.py",
}


def load(name):
    spec = importlib.util.spec_from_file_location("t_" + name, os.path.join(ROOT, TOOLS[name]))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Chain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="metals-test-")
        cls.fx = os.path.join(cls.tmp, "fx")
        subprocess.run([sys.executable, "-I", os.path.join(ROOT, "tests", "make_fixtures.py"), cls.fx],
                       check=True, capture_output=True)
        os.makedirs(os.path.join(cls.tmp, "trader"))
        shutil.copy(os.path.join(ROOT, "trader-budget", "config.example.json"),
                    os.path.join(cls.tmp, "trader", "config.json"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_tool(self, name, *args, ok=(0,)):
        r = subprocess.run([sys.executable, "-I", os.path.join(ROOT, TOOLS[name])] + list(args),
                           cwd=self.tmp, capture_output=True, text=True)
        self.assertIn(r.returncode, ok, "%s %s\n%s\n%s" % (name, args, r.stdout, r.stderr))
        return r.stdout

    def read(self, rel):
        with open(os.path.join(self.tmp, rel)) as fh:
            return json.load(fh)

    def test_1_chain(self):
        fx5 = os.path.join(self.fx, "5m")
        out = self.run_tool("scan", "orb", "--offline", fx5, "--symbols", "GOLD,SILVER", "--now", "2026-11-13 12:35")
        self.assertIn("GOLD", out)

        out = self.run_tool("entry", "check", "GOLD", "--offline", fx5, "--now", "2026-11-13 12:10", ok=(0, 1))
        self.assertIn("RANGE FORMING", out)
        out = self.run_tool("entry", "check", "GOLD", "--offline", fx5, "--now", "2026-11-13 12:35", "--write")
        self.assertIn("TRIGGERED 12:30", out)  # no entries before 12:30 (config)
        self.assertEqual(self.read("trader/entry.json")["symbol"], "GOLD")

        self.run_tool("exit", "plan", "--from", "trader/entry.json", "--offline", fx5,
                      "--now", "2026-11-13 12:35", "--write", "trader/plan.json")
        plan = self.read("trader/plan.json")
        self.assertLess(plan["stop"], plan["entry"])
        self.assertAlmostEqual(plan["target"] - plan["entry"], 2 * (plan["entry"] - plan["stop"]), places=1)
        self.assertEqual(plan["flat_by"], "23:15")

        out = self.run_tool("tm", "run", "--offline", fx5, "--now", "2026-11-13 12:35", "--seed", "19",
                            "--until", "23:15", "--write")
        self.assertIn("10,000 replays", out)

        out = self.run_tool("size", "--now", "2026-11-13 12:36", "--write")
        order = self.read("trader/orders.json")["orders"][0]
        risk = plan["entry"] - plan["stop"]
        oz = int(order["qty"])
        self.assertLessEqual(oz * risk, 100.0 + 1e-6)          # $100 max loss in the example config
        self.assertGreater((oz + 1) * risk, 100.0)              # and the biggest whole oz under it
        self.assertEqual(order["lots"], ("%.2f" % (oz / 100.0)).rstrip("0").rstrip("."))

        out = self.run_tool("risk", "--now", "2026-11-13 12:37")
        self.assertIn("PASS", out)
        out = self.run_tool("risk", "--now", "2026-11-13 22:30", "--no-write", ok=(1,))
        self.assertIn("no new entries after 22:00", out)
        out = self.run_tool("risk", "--now", "2026-12-25 13:00", "--no-write", ok=(1,))
        self.assertIn("Christmas", out)

        self.run_tool("alerts", "add", "--from-plan")
        out = self.run_tool("alerts", "check", "--offline", os.path.join(self.fx, "alerts"),
                            "--now", "2026-11-13 13:20", ok=(0, 1, 2))
        self.assertIn("GOLD", out)

    def test_2_news(self):
        out = self.run_tool("news", "--tickers", "GOLD", "SILVER", "--offline", os.path.join(self.fx, "news"),
                            "--now", "2026-11-13T08:40:00Z", "--dry-run", "--hours", "72")
        self.assertIn("tags: fed", out)
        self.assertIn("GOLD,SILVER", out)  # the silver story mentions gold too

    def test_3_daily_scan(self):
        self.run_tool("scan", "daily", "--offline", os.path.join(self.fx, "1d"), "--now", "2026-11-13 11:30",
                      "--no-write", ok=(0, 1))


class Units(unittest.TestCase):
    def test_symbols(self):
        for name in ("scan", "entry", "exit", "tm", "alerts"):
            m = load(name)
            self.assertEqual(m._ysym("gold"), "GC=F", name)
            self.assertEqual(m._ysym("XAUUSD"), "GC=F", name)
            self.assertEqual(m._ysym("SILVER"), "SI=F", name)
            self.assertEqual(m._ysym("XAGUSD"), "SI=F", name)
            self.assertEqual(m._ysym("GC=F"), "GC=F", name)
        self.assertEqual(load("news").yahoo_symbol("gold"), "GC=F")

    def test_dubai_clock(self):
        import datetime as dt
        m = load("entry")
        self.assertEqual(m.to_eastern(dt.datetime(2026, 11, 13, 8, 0)), dt.datetime(2026, 11, 13, 12, 0))
        self.assertEqual(m.session(dt.date(2026, 11, 13)), (dt.time(12, 0), dt.time(23, 30)))
        self.assertIsNone(m.session(dt.date(2026, 11, 14)))           # Saturday
        self.assertIsNone(m.session(dt.date(2026, 12, 25)))           # Christmas
        self.assertEqual(m.session(dt.date(2026, 11, 26))[1], dt.time(21, 0))  # Thanksgiving early close

    def test_sizing_lots_and_leverage(self):
        s = load("size")
        plan = {"symbol": "SILVER", "entry": 52.00, "stop": 51.80, "target": 52.40, "date": "2026-11-13"}
        r = s.size_trade(plan, {"budget": 10000, "max_loss_per_trade_usd": 100, "leverage": 20,
                                "cash_buffer_pct": 0, "max_position_pct": 100})
        self.assertEqual(r["qty"], 500)        # $100 / $0.20 = 500 oz = 0.1 lot (50 oz steps)
        self.assertEqual(r["lots"], "0.1")
        r = s.size_trade(plan, {"budget": 10000, "max_loss_per_trade_usd": 100, "leverage": 1,
                                "cash_buffer_pct": 0, "max_position_pct": 100})
        self.assertIn(r["bound_by"], ("position cap", "cash"))  # unleveraged: $10,000 buys 150 oz (3 x 50)
        self.assertEqual(r["qty"], 150)
        plan = {"symbol": "GOLD", "entry": 4000, "stop": 3800, "target": 4400}
        r = s.size_trade(plan, {"budget": 10000, "max_loss_per_trade_usd": 100, "leverage": 20})
        self.assertEqual(r["qty"], 0)          # 1 oz risks $200 > $100
        self.assertIn("No order", r["refusal"])


if __name__ == "__main__":
    unittest.main()
