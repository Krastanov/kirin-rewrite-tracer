# Pinned headed-Chrome fixture

Browser verification uses only Chrome for Testing `151.0.7922.47`, revision
`r1654411`, and its matching ChromeDriver for `linux64`.

Provision these two archives outside the repository:

- `https://storage.googleapis.com/chrome-for-testing-public/151.0.7922.47/linux64/chrome-linux64.zip`
  — SHA-256
  `14ac03a67e154e3f8bbc57e03ef03315fda8fedff8e045eee8b31500283a33f4`
- `https://storage.googleapis.com/chrome-for-testing-public/151.0.7922.47/linux64/chromedriver-linux64.zip`
  — SHA-256
  `2faa72828261cd3c5ff00cbc71cfca57a12c26c1406e084e1a34d8d90e292140`

Extract them beneath
`~/.cache/kirin-rewrite-tracer/chrome-for-testing/151.0.7922.47/`, or point
`KRT_CHROME_FOR_TESTING_ROOT` at an equivalent directory. The harness hashes both
archives, invokes both extracted binaries for their exact versions, and verifies the
versions Selenium actually starts.

Run the headed tests with the required producer runtime and a sufficiently large Xvfb
screen:

```console
xvfb-run -a -s '-screen 0 4096x3072x24' \
  uv run --python 3.13.11 pytest -m browser
```

The session uses a temporary profile, cache, and download directory under `/tmp`,
disables page networking through CDP, and retains no screenshots, reports, or browser
artifacts.

[`.github/scripts/provision_chrome.py`](../../.github/scripts/provision_chrome.py)
performs exactly this provision for continuous integration. It reads every URL, hash,
and path from [`browser_harness.py`](../browser_harness.py), so the pin has one source.
