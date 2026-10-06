"""Generate reproducible CSV analytics and a self-contained HTML report."""
import argparse
import csv
import html
import json
from pathlib import Path
from .models import bootstrap, fx_forward, fx_pv, swap_pv, par_swap_rate, sensitivity


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(quotes_path, output):
    q = json.loads(Path(quotes_path).read_text())
    curves = {ccy: bootstrap(q[ccy]['deposits'], q[ccy]['swaps']) for ccy in ('USD', 'EUR')}
    d, f = curves['USD'], curves['EUR']
    spot = q['spot_usd_per_eur']
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for ccy, c in curves.items():
        for t, df in zip(c.times[1:], c.dfs[1:]):
            rows.append(dict(currency=ccy, years=t, discount_factor=df, continuous_zero=c.zero(t)))
    write_csv(out/'curves.csv', rows)
    calibration = []
    for ccy, c in curves.items():
        for t, r in q[ccy]['deposits']:
            calibration.append(dict(currency=ccy, instrument='deposit', maturity=t,
                input_rate=r, repriced_rate=(1/c.df(t)-1)/t))
        for t, r in q[ccy]['swaps']:
            calibration.append(dict(currency=ccy, instrument='swap', maturity=t,
                input_rate=r, repriced_rate=par_swap_rate(c,t)))
    write_csv(out/'calibration.csv', calibration)
    forwards = [dict(years=t, usd_per_eur=fx_forward(spot,d,f,t),
                     forward_points=(fx_forward(spot,d,f,t)-spot)*10000) for t in (0.25,0.5,1,2,3,5)]
    write_csv(out/'forwards.csv', forwards)
    maturity, notional = 2.0, 1_000_000.0
    strike, fixed = fx_forward(spot,d,f,maturity), par_swap_rate(d,5)
    fxprice = lambda dc, fc, s=spot: fx_pv(s,strike,notional,dc,fc,maturity)
    risk = []
    for ccy, c in curves.items():
        pricer = (lambda x: fxprice(x,f)) if ccy == 'USD' else (lambda x: fxprice(d,x))
        for i,t in enumerate(c.times[1:],1):
            risk.append(dict(instrument='2Y EURUSD forward', currency=ccy, pillar_years=t,
                             signed_pv_change_per_bp=sensitivity(pricer,c,pillar=i)))
    for i,t in enumerate(d.times[1:],1):
        risk.append(dict(instrument='5Y USD pay-fixed swap', currency='USD', pillar_years=t,
                         signed_pv_change_per_bp=sensitivity(lambda x:swap_pv(x,5,fixed,notional),d,pillar=i)))
    write_csv(out/'bucket_risk.csv', risk)
    scenarios = []
    for name, shock, usd_bp, eur_bp in [('base',0,0,0),('spot_up_1pct',.01,0,0),
                ('usd_up_25bp',0,25,0),('eur_up_25bp',0,0,25),('both_up_25bp',0,25,25),
                ('combined',-.01,25,-25)]:
        scenarios.append(dict(scenario=name, fx_pv_usd=fxprice(d.bump(usd_bp),f.bump(eur_bp),spot*(1+shock)),
            swap_pv_usd=swap_pv(d.bump(usd_bp),5,fixed,notional)))
    write_csv(out/'scenarios.csv', scenarios)
    tables = ''
    for title, data in [('Calibration',calibration),('FX forwards',forwards),('Key-rate risk',risk),('Scenarios',scenarios)]:
        tables += '<h2>'+title+'</h2><table><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in data[0])+'</tr>'
        for row in data:
            tables += '<tr>'+''.join('<td>'+html.escape(f'{v:.6f}' if isinstance(v,float) else str(v))+'</td>' for v in row.values())+'</tr>'
        tables += '</table>'
    report = '<!doctype html><meta charset="utf-8"><title>FX & Rates Research Lab</title><style>body{font:16px system-ui;background:#101a2b;color:#e5ecf6;margin:40px;max-width:1200px}h1{color:#68daca}table{border-collapse:collapse;width:100%;font-size:13px}td,th{text-align:left;padding:9px;border-bottom:1px solid #34435b}th{color:#68daca}p{line-height:1.6}</style><h1>FX & Rates Research Lab</h1><p>Synthetic quotes • USD per EUR • Single-curve swaps • Log-linear discount factors</p><p>Zero-pillar sensitivities are signed PV changes per +1bp, not quote-bucket hedge notionals. Educational model: no cross-currency basis, calendars, collateral curves or credit adjustments.</p>'+tables
    (out/'report.html').write_text(report)
    return scenarios


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quotes', default='data/quotes.json')
    parser.add_argument('--output', default='results')
    args = parser.parse_args()
    run(args.quotes,args.output)
    print(f'Generated analytics in {args.output}')

if __name__ == '__main__':
    main()
