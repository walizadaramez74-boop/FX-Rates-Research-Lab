"""Single-curve, deterministic pricing with explicit conventions."""
from dataclasses import dataclass
import math
from bisect import bisect_left


def finite(*values):
    if not all(math.isfinite(x) for x in values):
        raise ValueError('Inputs must be finite')


@dataclass(frozen=True)
class Curve:
    """Log-linear discount factors. No extrapolation. Time in years."""
    times: tuple
    dfs: tuple

    def __post_init__(self):
        if len(self.times) != len(self.dfs) or len(self.times) < 2:
            raise ValueError('At least two equally sized pillars required')
        finite(*self.times, *self.dfs)
        if self.times[0] != 0 or self.dfs[0] != 1:
            raise ValueError('Curve must start at (0, 1)')
        if any(b <= a for a, b in zip(self.times, self.times[1:])):
            raise ValueError('Times must strictly increase')
        if any(d <= 0 for d in self.dfs):
            raise ValueError('Discount factors must be positive')

    def df(self, t):
        finite(t)
        if not 0 <= t <= self.times[-1]:
            raise ValueError('Maturity outside curve coverage')
        if t == 0:
            return 1.0
        j = bisect_left(self.times, t)
        a, b = self.times[j-1], self.times[j]
        weight = (t-a)/(b-a)
        return math.exp((1-weight)*math.log(self.dfs[j-1]) + weight*math.log(self.dfs[j]))

    def zero(self, t):
        if t <= 0:
            raise ValueError('Zero rate requires positive maturity')
        return -math.log(self.df(t))/t

    def bump(self, bp=1.0, pillar=None):
        """Bump continuous zero rates by bp; pillar index excludes origin."""
        finite(bp)
        if pillar is not None and not 1 <= pillar < len(self.times):
            raise ValueError('Invalid pillar')
        return Curve(self.times, tuple(d*math.exp(-bp*1e-4*t)
                     if pillar is None or i == pillar else d
                     for i, (t, d) in enumerate(zip(self.times, self.dfs))))


def schedule(maturity, frequency=2):
    finite(maturity)
    if maturity <= 0 or frequency not in (1, 2, 4, 12):
        raise ValueError('Positive maturity and supported payment frequency required')
    count = round(maturity*frequency)
    if not math.isclose(count, maturity*frequency, abs_tol=1e-9):
        raise ValueError('Stub schedules unsupported')
    return tuple(i/frequency for i in range(1, count+1))


def annuity(curve, maturity, frequency=2):
    return sum(curve.df(t)/frequency for t in schedule(maturity, frequency))


def par_swap_rate(curve, maturity, frequency=2):
    return (1-curve.df(maturity))/annuity(curve, maturity, frequency)


def swap_pv(curve, maturity, fixed_rate, notional=1.0, frequency=2):
    """Pay fixed / receive floating, spot starting, single curve."""
    finite(fixed_rate, notional)
    return notional*(1-curve.df(maturity)-fixed_rate*annuity(curve, maturity, frequency))


def bootstrap(deposits, swaps, frequency=2):
    """Deposits: simple annual rates. Swaps: par fixed rates. Ordered maturities."""
    times, dfs = [0.0], [1.0]
    for t, rate in deposits:
        finite(t, rate)
        if t <= times[-1] or 1+rate*t <= 0:
            raise ValueError('Invalid deposit quote/order')
        times.append(t)
        dfs.append(1/(1+rate*t))
    if len(times) < 2:
        raise ValueError('At least one deposit required')
    for t, rate in swaps:
        finite(t, rate)
        if t <= times[-1]:
            raise ValueError('Swap maturities must extend curve')
        schedule(t, frequency)
        def residual(log_df):
            candidate = Curve(tuple(times+[t]), tuple(dfs+[math.exp(log_df)]))
            return swap_pv(candidate, t, rate, frequency=frequency)
        lo, hi = -40.0, 10.0
        if residual(lo)*residual(hi) >= 0:
            raise ValueError('Cannot bracket discount factor')
        for _ in range(150):
            mid = (lo+hi)/2
            if residual(lo)*residual(mid) <= 0:
                hi = mid
            else:
                lo = mid
        times.append(t)
        dfs.append(math.exp((lo+hi)/2))
    return Curve(tuple(times), tuple(dfs))


def fx_forward(spot, domestic, foreign, maturity):
    finite(spot, maturity)
    if spot <= 0:
        raise ValueError('Spot must be positive')
    return spot*foreign.df(maturity)/domestic.df(maturity)


def fx_pv(spot, strike, foreign_notional, domestic, foreign, maturity):
    """Buy foreign currency / pay domestic at maturity; PV in domestic currency."""
    finite(strike, foreign_notional)
    if strike <= 0:
        raise ValueError('Strike must be positive')
    return foreign_notional*domestic.df(maturity)*(fx_forward(spot, domestic, foreign, maturity)-strike)


def sensitivity(pricer, curve, bp=1.0, pillar=None):
    """Signed PV change for +1bp, central difference; bumps zero pillars, not quotes."""
    if bp <= 0:
        raise ValueError('Positive bump required')
    return (pricer(curve.bump(bp, pillar))-pricer(curve.bump(-bp, pillar)))/(2*bp)
