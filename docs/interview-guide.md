# Explain this project in an interview

Begin with the quote convention: USD per EUR. A forward exchanges one currency
for another at a future date. Pricing discounts both promised cash flows, rather
than treating an FX forward as a forecast of the future spot rate.

Explain deposit bootstrapping first: a deposit with simple annual rate r and time
T gives discount factor 1/(1+rT). For each swap maturity, solve the final discount
factor so the fixed leg equals the floating leg, interpolating intermediate cash
flows. Show calibration.csv: input quotes must reprice.

Explain zero-pillar risk carefully: perturb one continuously compounded pillar,
rebuild the interpolated curve and reprice. This is not a quote-bucket hedge. To
get hedge notionals, bump the input market quotes and rebootstrap, then solve the
instrument-risk matrix. That is a possible future extension.

Explain why there are two FX risks: changing either domestic or foreign rates
changes forward value. Increasing USD rates raises the USD-per-EUR forward rate
in this simplified setting; increasing EUR rates lowers it. Raising both by the
same continuous-zero shift leaves the forward ratio unchanged, but can change
the PV of an already off-market contract through discounting.

Be ready to discuss why production swaps need projection/discount curves and
why basis, day-count conventions, settlement and collateral matter. Do not say
you built a production pricing engine or used historical market data.
