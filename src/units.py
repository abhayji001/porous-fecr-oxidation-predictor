import math
from .constants import K_B_EV
def ssa_cm2_per_g(value, unit):
  u = unit.strip().lower().replace("**2","^2")
  f = {"m2/g":10000,"m^2/g":10000,"m²/g":10000,"cm2/g":1,"cm^2/g":1,"cm²/g":1}
  if u not in f: raise ValueError(f"unknown ssa unit {unit}")
  r = float(value)*f[u]
  if r < 10 or r > 100000: raise ValueError("ssa outside 10 to 100000 cm2/g, paper may have printed the wrong unit")
  return r
def mass_gain_mg_cm2(pct, ssa): return float(pct)*10.0/float(ssa)
def oxide_thickness_um(dm, s, rho, eps):
  if eps < 0 or eps >= 1: raise ValueError("eps must be 0 to <1")
  return 10.0*float(dm)*float(s)/(float(rho)*(1.0-float(eps)))
def kp_from_point(dm, t_h):
  if t_h <= 0: raise ValueError("t_h <=0")
  if dm < 0: raise ValueError("dm <0")
  return (float(dm)/1000.0)**2/(float(t_h)*3600.0)
def kp_consistent(dm, t_h, kp, tol=0.25):
  return abs(kp_from_point(dm,t_h)/float(kp)-1) <= tol
def arrhenius(k0, ea, Tc): return float(k0)*math.exp(-float(ea)/(K_B_EV*(float(Tc)+273.15)))
