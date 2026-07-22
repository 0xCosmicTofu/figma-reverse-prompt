import math

# ---------- colour math ----------
def hex2rgb(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def rgb2hex(r): return '#%02X%02X%02X'%tuple(max(0,min(255,round(c))) for c in r)
def _lin(c):
    c/=255
    return c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
def lum(h):
    r,g,b=hex2rgb(h); return 0.2126*_lin(r)+0.7152*_lin(g)+0.0722*_lin(b)
def contrast(a,b):
    la,lb=lum(a),lum(b); hi,lo=max(la,lb),min(la,lb)
    return (hi+0.05)/(lo+0.05)

# sRGB <-> OKLab (Bjorn Ottosson)
def _s2l(c):
    c/=255
    return c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
def _l2s(c):
    c = 12.92*c if c<=0.0031308 else 1.055*(c**(1/2.4))-0.055
    return max(0,min(255,round(c*255)))
def hex2oklab(h):
    r,g,b=[_s2l(x) for x in hex2rgb(h)]
    l=0.4122214708*r+0.5363325363*g+0.0514459929*b
    m=0.2119034982*r+0.6806995451*g+0.1073969566*b
    s=0.0883024619*r+0.2817188376*g+0.6299787005*b
    l,m,s=l**(1/3),m**(1/3),s**(1/3)
    return (0.2104542553*l+0.7936177850*m-0.0040720468*s,
            1.9779984951*l-2.4285922050*m+0.4505937099*s,
            0.0259040371*l+0.7827717662*m-0.8086757660*s)
def oklab2hex(L,a,b):
    l=(L+0.3963377774*a+0.2158037573*b)**3
    m=(L-0.1055613458*a-0.0638541728*b)**3
    s=(L-0.0894841775*a-1.2914855480*b)**3
    r=+4.0767416621*l-3.3077115913*m+0.2309699292*s
    g=-1.2684380046*l+2.6097574011*m-0.3413193965*s
    bb=-0.0041960863*l-0.7034186147*m+1.7076147010*s
    return rgb2hex((_l2s(r),_l2s(g),_l2s(bb)))
def oklch(h):
    L,a,b=hex2oklab(h); import math; return L,math.hypot(a,b),math.atan2(b,a)
def from_lch(L,C,H): import math; return oklab2hex(L,C*math.cos(H),C*math.sin(H))

def repair(fg,bg,target,direction):
    """Move fg lightness in OKLCH (preserve hue/chroma) until contrast>=target."""
    if contrast(fg,bg)>=target: return fg,False
    L,C,H=oklch(fg)
    lo,hi=(L,1.0) if direction=='lighten' else (0.0,L)
    best=from_lch(1.0 if direction=='lighten' else 0.0,C,H)
    # binary search on L toward the extreme that raises contrast
    for _ in range(40):
        mid=(lo+hi)/2
        cand=from_lch(mid,C,H)
        if contrast(cand,bg)>=target:
            best=cand
            if direction=='lighten': hi=mid
            else: lo=mid
        else:
            if direction=='lighten': lo=mid
            else: hi=mid
    # if still failing at extreme (chroma too high), drop chroma and retry once
    if contrast(best,bg)<target:
        for c in [C*0.6,C*0.3,0]:
            cand=from_lch(1.0 if direction=='lighten' else 0.0,c,H)
            if contrast(cand,bg)>=target: return cand,True
    return best,True


# ---------------------------------------------------------------------------
# Usage: repair(fg, bg, target, direction) moves fg's OKLCH lightness (hue and
# chroma preserved) until contrast(fg,bg) >= target. Falls back to reducing
# chroma if the target is unreachable at the lightness extreme.
#   AA : 4.5 normal text · 3.0 large text (>=24px, or >=18.66px bold) · 3.0 non-text
#   AAA: 7.0 normal text · 4.5 large text
# Two levers, in order: (1) repair the FOREGROUND; (2) if it is already at an
# extreme and still fails, repair the BACKGROUND (e.g. a mid-amber CTA cannot
# carry AA text as black OR white -- deepen the fill and use light text).
