import pytest
import math
import datetime
import os
from dotenv import load_dotenv

# PASS/FAIL/ERROR counters
_results_counter = {'passed': 0, 'failed': 0, 'error': 0}

load_dotenv()

def pytest_addoption(parser):
    parser.addoption(
        "--ota-version",
        action="store",
        default=os.getenv("OTA_VERSION", "N/A"),
        help="OTA Version tested"
    )
    parser.addoption(
        "--env",
        action="store",
        default=os.getenv("ENVIRONMENT", "Staging"),
        help="Environment (e.g., staging, prod)"
    )
    parser.addoption(
        "--device-id",
        action="store",
        default=os.getenv("DEVICE_ID", "Unknown"),
        help="Device ID under test"
    )
    parser.addoption(
        "--device-ip",
        action="store",
        default=os.getenv("DEVICE_IP", "Unknown"),
        help="Device IP address under test"
    )


def pytest_configure(config):
    global custom_env_info
    custom_env_info = {
        "Device ID": config.getoption("--device-id"),
        "Device IP": config.getoption("--device-ip"),
        "OTA Version": config.getoption("--ota-version"),
        "Environment": config.getoption("--env"),
        "Start Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    # Always attach description (even if failure in setup)
    if not hasattr(rep, 'description'):
        rep.description = (getattr(getattr(item, 'obj', None), '__doc__', '') or '').strip()
    phase = rep.when
    res_lower = rep.outcome.lower()
    # Count results for all phases; only increment once per test final outcome
    if phase == 'call':
        if res_lower in _results_counter:
            _results_counter[res_lower] += 1
    elif phase == 'setup' and res_lower in ('failed', 'error'):
        # Setup error -> treat as error
        _results_counter['error'] += 1

@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_header(cells):
    cells.insert(2, '<th>Description</th>')

@pytest.hookimpl(optionalhook=True)
def pytest_html_results_table_row(report, cells):
    desc = getattr(report, 'description', '')
    cells.insert(2, f'<td>{desc}</td>')

@pytest.hookimpl(optionalhook=True)
def pytest_html_results_summary(prefix, summary, postfix):
    """Inject interactive hover pie chart (no shadow) with static percentage labels and center title + black headers + Total filter."""

    summary.clear()
    env_table = (
    "<div style='margin-top:10px; margin-bottom:20px;'>"
    "<h3 style='color:#000;text-align:left;margin-bottom:6px;'>Device Details</h3>"
    "<table style='border-collapse:collapse;width:20%;font-size:13px;'>"
    )
    for k, v in custom_env_info.items():
        env_table += (
            f"<tr>"
            f"<td style='border:1px solid #ccc;padding:4px 8px;font-weight:bold;width:30%;'>{k}</td>"
            f"<td style='border:1px solid #ccc;padding:4px 8px;width:70%;'>{v}</td>"
            f"</tr>"
        )
    env_table += "</table></div>"


    postfix.extend([env_table])
    passed = _results_counter['passed']
    failed = _results_counter['failed']
    errors = _results_counter['error']
    display_failed = failed + errors
    total = passed + display_failed
    if total == 0:
        return

    pass_frac = passed / total
    fail_frac = display_failed / total

    R = 110
    CX = CY = 115

    def arc_path(start_frac, sweep_frac, fill_label):
        if sweep_frac <= 0:
            return ''
        start_ang = (start_frac * 360.0) - 90.0  # start at top
        end_ang = ((start_frac + sweep_frac) * 360.0) - 90.0
        start_rad = math.radians(start_ang)
        end_rad = math.radians(end_ang)
        x1 = CX + R * math.cos(start_rad)
        y1 = CY + R * math.sin(start_rad)
        x2 = CX + R * math.cos(end_rad)
        y2 = CY + R * math.sin(end_rad)
        large_flag = 1 if sweep_frac * 360.0 > 180.0 else 0
        return f"<path d='M {CX} {CY} L {x1:.3f} {y1:.3f} A {R} {R} 0 {large_flag} 1 {x2:.3f} {y2:.3f} Z' fill='{{color}}' data-label='{fill_label}' data-count='{{count}}' data-pct='{{pct}}'></path>"

    def label_text(start_frac, sweep_frac, pct_text, fill_label):
        if sweep_frac <= 0:
            return ''
        mid_frac = start_frac + (sweep_frac / 2.0)
        mid_ang = (mid_frac * 360.0) - 90.0
        mid_rad = math.radians(mid_ang)
        # radius for label slightly inward
        r_txt = R * 0.55
        x = CX + r_txt * math.cos(mid_rad)
        y = CY + r_txt * math.sin(mid_rad)
        return f"<text x='{x:.3f}' y='{y:.3f}' text-anchor='middle' dominant-baseline='middle' font-size='13' fill='#000' data-label='{fill_label}' data-pct='{pct_text}'>{pct_text}</text>"

    pass_pct = f"{pass_frac*100:.1f}%"
    fail_pct = f"{fail_frac*100:.1f}%"

    pass_path = arc_path(0, pass_frac, 'Pass').replace('{color}', '#0A640A').replace('{count}', str(passed)).replace('{pct}', pass_pct)
    fail_path = arc_path(pass_frac, fail_frac, 'Fail/Error').replace('{color}', '#B52525').replace('{count}', str(display_failed)).replace('{pct}', fail_pct)

    pass_label = label_text(0, pass_frac, pass_pct, 'Pass')
    fail_label = label_text(pass_frac, fail_frac, fail_pct, 'Fail/Error')

    # If one slice == 100%, ensure we draw full circle path
    if passed == total:
        pass_path = f"<circle cx='{CX}' cy='{CY}' r='{R}' fill='#0A640A' data-label='Pass' data-count='{passed}' data-pct='{pass_pct}'></circle>"
        fail_path = ''
        pass_label = f"<text x='{CX}' y='{CY}' text-anchor='middle' dominant-baseline='middle' font-size='16' fill='#fff' font-weight='bold'>{pass_pct}</text>"
        fail_label = ''
    elif display_failed == total:
        fail_path = f"<circle cx='{CX}' cy='{CY}' r='{R}' fill='#B52525' data-label='Fail/Error' data-count='{display_failed}' data-pct='{fail_pct}'></circle>"
        pass_path = ''
        fail_label = f"<text x='{CX}' y='{CY}' text-anchor='middle' dominant-baseline='middle' font-size='16' fill='#fff' font-weight='bold'>{fail_pct}</text>"
        pass_label = ''

    pie_html = (
        "<div style='position:absolute;top:12px;right:12px;z-index:999;"\
        "padding:6px 10px;border:1px solid #e6e6e6;border-radius:6px;"\
        "background:#fdfdfd'>"\
        "<div style='font-weight:bold;text-align:center;margin:4px 0'>Test Cases Result</div>"\
        "<div id='fe-pie-wrap' style='position:relative;width:230px;height:230px;margin:0 auto'>"\
        "<svg width='230' height='230' viewBox='0 0 230 230'>"\
        "<circle cx='115' cy='115' r='110' fill='#ffffff'></circle>"\
        + pass_path + fail_path + pass_label + fail_label +
        "</svg>"\
        "<div id='fe-tooltip' style='position:absolute;top:8px;left:8px;padding:4px 6px;"\
        "background:#222;color:#fff;font-size:11px;border-radius:4px;pointer-events:none;opacity:0;"\
        "transition:opacity .15s'></div></div>"\
        f"<div style='font-size:11px;margin-top:4px;color:#000'>Pass: {passed} &nbsp; Fail/Error: {display_failed}</div>"\
        "</div>"\
        "<script>(function(){const wrap=document.getElementById('fe-pie-wrap');if(!wrap)return;"\
        "const tip=wrap.querySelector('#fe-tooltip');wrap.querySelectorAll('path,circle,text').forEach(p=>{"\
        "p.addEventListener('mousemove',e=>{tip.style.opacity=1;const lbl=p.getAttribute('data-label');const pct=p.getAttribute('data-pct');const cnt=p.getAttribute('data-count');"\
        "tip.textContent=(lbl?lbl+': ':'')+(cnt?cnt+' ':'')+(pct? '('+pct+')':'');tip.style.left=(e.offsetX+10)+'px';"\
        "tip.style.top=(e.offsetY+10)+'px';});p.addEventListener('mouseleave',()=>{tip.style.opacity=0;});});})();</script>"
    )

    center_css = "<style>#title{text-align:center;}#results-table th{color:#000;font-weight:bold!important;}#results-table td{color:#000!important;}</style>"
    header_enhance = "<style>.fe-header-wrapper{position:relative;width:100%;display:flex;justify-content:center;align-items:center;margin:0 0 10px 0;} .fe-header-wrapper img{position:absolute;left:0;top:0;height:30px;width:auto;} h1#title{margin:0 auto;text-align:center;width:100%;} @media (max-width:900px){.fe-header-wrapper img{height:36px;}} </style>"\
        "<script>(function(){var h=document.getElementById('title');if(!h)return; if(!h.closest('.fe-header-wrapper')){var wrap=document.createElement('div');wrap.className='fe-header-wrapper';var img=document.createElement('img');img.alt='Logo';img.src='logo.png';/* replace with actual path or base64 */h.parentNode.insertBefore(wrap,h);wrap.appendChild(h);wrap.appendChild(img);} h.textContent='FleetEdge Automation';})();</script>"

    # Script to add Total filter checkbox that toggles all status checkboxes
    total_filter_script = "<script>(function(){function init(){var summary=document.querySelector('.summary');if(!summary)return;var p=summary.querySelector('p');if(!p||p.querySelector('#total-filter'))return;var total=document.createElement('input');total.type='checkbox';total.id='total-filter';total.checked=true;var label=document.createElement('label');label.htmlFor='total-filter';label.textContent=' Total';var sep=document.createTextNode(', ');p.insertBefore(sep,p.firstChild);p.insertBefore(label,sep);p.insertBefore(total,label);function syncFromTotal(){p.querySelectorAll('input[data-status]').forEach(cb=>{cb.checked=total.checked;cb.dispatchEvent(new Event('change'));});}total.addEventListener('change',syncFromTotal);p.querySelectorAll('input[data-status]').forEach(cb=>{cb.addEventListener('change',()=>{var all=Array.from(p.querySelectorAll('input[data-status]')).every(x=>x.checked);total.checked=all;});});syncFromTotal();}if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init);}else{init();}})();</script>"

    # Build a table for test case counts
    results_table = "<div style='margin-top:20px;'>"
    results_table += "<h3 style='color:#000;text-align:left;margin-bottom:6px;'>Test Case Summary</h3>"
    results_table += "<table style='border-collapse:collapse;width:20%;font-size:13px;'>"
    results_table += "<tr><th style='border:1px solid #ccc;padding:4px;'>Result</th><th style='border:1px solid #ccc;padding:4px;'>Count</th></tr>"

    # Add each status
    for k, v in {
        "Passed": passed,
        "Fail/Error": display_failed,
        "Total": total
    }.items():
        results_table += f"<tr><td style='border:1px solid #ccc;padding:4px;font-weight:bold;'>{k}</td>"
        results_table += f"<td style='border:1px solid #ccc;padding:4px;text-align:center;'>{v}</td></tr>"

    results_table += "</table></div>"

    prefix.extend([center_css, header_enhance, total_filter_script, pie_html, results_table])

@pytest.hookimpl(optionalhook=True)
def pytest_html_report_title(report):
    report.title = "FleetEdge Automation"
