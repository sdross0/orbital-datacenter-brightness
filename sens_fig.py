import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import lsm as L

N=500_000
cons=L.build_sso(N,relax_deg=10.0); scale=N/L.total_of(cons)
r_obs,up,east,north=L.observer(37.23,18.00); s=L.sun_dir(0.0)
V={}
for m in ("boley","mini"):
    v=[]
    for c in cons:
        p=L.propagate(c,0.0)
        f=L.observe if m=="boley" else L.observe_empirical
        alt,az,d,Vv,lit=f(p,r_obs,up,east,north,s)
        v.append(Vv[lit&(alt>-0.005)&np.isfinite(Vv)])
    V[m]=np.concatenate(v)

d=np.linspace(-0.6,1.2,181)
cb=np.array([(V["boley"]<6.0-x).sum()*scale for x in d])
cm=np.array([(V["mini"] <6.0-x).sum()*scale for x in d])

try:
    fp=fm.FontProperties(fname="/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Regular.otf")
    fb=fm.FontProperties(fname="/usr/share/fonts/opentype/urw-base35/NimbusSansNarrow-Bold.otf")
except Exception:
    fp=fb=None

BG="#0b1020"; ORA="#ffd6be"; BLU="#bee0ff"; TXT="#dfe6f2"; GRID="#26304a"
fig,ax=plt.subplots(figsize=(9,5.6),dpi=170)
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
ax.plot(d,cb,color=ORA,lw=2.6)
ax.plot(d,cm,color=BLU,lw=2.6)
ax.axvline(0,color=GRID,lw=1.2,ls="--")
ax.set_yscale("log")
ax.set_xlim(-0.6,1.2); ax.set_ylim(1.8e3,1.35e5)
ax.grid(True,which="major",color=GRID,lw=0.7)
ax.set_axisbelow(True)
for sp in ax.spines.values(): sp.set_color(GRID)
ax.tick_params(colors=TXT,labelsize=11)
for lab in ax.get_xticklabels()+ax.get_yticklabels():
    if fp: lab.set_fontproperties(fp)
ax.set_yticks([2e3,5e3,1e4,2e4,5e4,1e5])
ax.set_yticklabels(["2,000","5,000","10,000","20,000","50,000","100,000"])
ax.set_xlabel("systematic brightness error  (magnitudes fainter than modeled)",
              color=TXT,fontsize=12,fontproperties=fp,labelpad=9)
ax.set_ylabel("satellites visible to the naked eye",color=TXT,fontsize=12,
              fontproperties=fp,labelpad=9)
ax.set_title("Same error, very different consequence",color="#ffffff",
             fontsize=17,fontproperties=fb,pad=34,loc="left")
ax.text(0.0,1.018,"sunset, 500,000 satellites, V < 6, Blacksburg VA",
        transform=ax.transAxes,color="#93a2bf",fontsize=11,fontproperties=fp)
ax.annotate("unmitigated reference\n445 satellites per 0.1 mag  (0.7%)",
            xy=(0.70,cb[np.argmin(abs(d-0.70))]),xytext=(0.16,8.6e4),
            color=ORA,fontsize=11.5,fontproperties=fp,
            arrowprops=dict(arrowstyle="-",color=ORA,lw=1.0,alpha=.55))
ax.annotate("optimistic mitigated reference\n1,255 satellites per 0.1 mag  (10.9%)",
            xy=(0.30,cm[np.argmin(abs(d-0.30))]),xytext=(-0.56,3.0e3),
            color=BLU,fontsize=11.5,fontproperties=fp,
            arrowprops=dict(arrowstyle="-",color=BLU,lw=1.0,alpha=.55))
ax.text(-0.015,0.035,"as modeled",transform=ax.get_xaxis_transform(),
        va="bottom",ha="right",color="#8b98b5",fontsize=10,fontproperties=fp)
fig.tight_layout()
fig.savefig("sensitivity.png",facecolor=BG)
print("wrote sensitivity.png")
print("check: at 0.0 -> %.0f / %.0f" % (cb[np.argmin(abs(d))], cm[np.argmin(abs(d))]))
