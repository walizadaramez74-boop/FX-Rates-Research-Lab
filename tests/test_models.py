import json
import math
from pathlib import Path
import pytest
from fx_rates.models import Curve, bootstrap, fx_forward, fx_pv, par_swap_rate, swap_pv, sensitivity, schedule
from fx_rates.cli import run


def flat(rate=.04):
    return Curve((0.,1.,5.,10.), (1.,math.exp(-rate),math.exp(-5*rate),math.exp(-10*rate)))


def test_interpolation_matches_flat_curve():
    c=flat()
    assert c.df(2.5)==pytest.approx(math.exp(-.04*2.5))
    assert c.zero(3)==pytest.approx(.04)


@pytest.mark.parametrize('times,dfs', [((0,1,1),(1,.9,.8)),((0,1),(1,0)),((0,1),(1,float('nan'))),((1,2),(1,.9))])
def test_invalid_curve(times,dfs):
    with pytest.raises(ValueError): Curve(times,dfs)


@pytest.mark.parametrize('t',[-1,11,float('nan')])
def test_no_extrapolation(t):
    with pytest.raises(ValueError): flat().df(t)


def test_negative_rates_supported():
    assert flat(-.01).df(5)>1


def test_quote_repricing():
    q=json.loads(Path('data/quotes.json').read_text())
    for ccy in ('USD','EUR'):
        c=bootstrap(q[ccy]['deposits'],q[ccy]['swaps'])
        for t,r in q[ccy]['deposits']:
            assert (1/c.df(t)-1)/t==pytest.approx(r,abs=1e-12)
        for t,r in q[ccy]['swaps']:
            assert par_swap_rate(c,t)==pytest.approx(r,abs=1e-12)


def test_cip_and_zero_inception_pv():
    d,f=flat(.04),flat(.02)
    forward=fx_forward(1.1,d,f,2)
    assert forward==pytest.approx(1.1*math.exp(.02*2))
    assert fx_pv(1.1,forward,1e6,d,f,2)==pytest.approx(0,abs=1e-8)


def test_domestic_and_foreign_risk_signs():
    d,f=flat(.04),flat(.02)
    k=fx_forward(1.1,d,f,2)
    assert sensitivity(lambda c: fx_pv(1.1,k,1e6,c,f,2),d)>0
    assert sensitivity(lambda c: fx_pv(1.1,k,1e6,d,c,2),f)<0


def test_swap_zero_pv_and_pay_fixed_risk():
    c=flat()
    k=par_swap_rate(c,5)
    assert swap_pv(c,5,k,1e6)==pytest.approx(0,abs=1e-8)
    assert sensitivity(lambda x:swap_pv(x,5,k,1e6),c)>0


def test_bucket_risk_sums_to_parallel():
    c=flat()
    fn=lambda x:swap_pv(x,5,.04,1e6)
    buckets=sum(sensitivity(fn,c,bp=.01,pillar=i) for i in range(1,len(c.times)))
    assert buckets==pytest.approx(sensitivity(fn,c,bp=.01),rel=1e-7)


def test_fx_delta_analytic():
    d,f=flat(.04),flat(.02)
    h=1e-5
    delta=(fx_pv(1.1+h,1.1,1e6,d,f,2)-fx_pv(1.1-h,1.1,1e6,d,f,2))/(2*h)
    assert delta==pytest.approx(1e6*f.df(2))


def test_invalid_bootstrap_and_stub():
    with pytest.raises(ValueError): bootstrap([(1,-2)],[])
    with pytest.raises(ValueError): schedule(1.2)


def test_report_end_to_end(tmp_path):
    rows=run('data/quotes.json',tmp_path)
    assert abs(rows[0]['fx_pv_usd'])<1e-8
    assert (tmp_path/'report.html').is_file()
    assert (tmp_path/'calibration.csv').read_text().startswith('currency')
