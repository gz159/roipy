'''
NOTE: would be awesome to have stand-alone python version additions:
    
    - georeferencing (then output at specific lat/lon points to compare to GPS...)
    - output tinker parameters to use as initial guess in inversion
    - multiple sources
    - ginput profiles
'''

# Autogenerated with SMOP version 0.22
# /Users/scott/Library/Enthought/Canopy_64bit/User/bin/smop -v calc_okada.m -o calc_okada.py
from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
#import roipy as rp
import examples


def fBi(sig,eta,parvec,p,q):
    '''
    Utility function for calc_okada
    f1a,f2a,f3a = fBi(rotx+L, p, parvec, p, q)

    '''
    # Unpack Fault Parameters
    a, delta, fault_type = parvec
    
    cosd = np.cos(delta)
    sind = np.sin(delta)
    tand = np.tan(delta)
    #cosd2 = np.cos(delta)**2 #comment un-used variables
    sind2 = np.sin(delta)**2
    cssnd = np.cos(delta) * np.sin(delta)
    
    R = np.sqrt(sig**2 + eta**2 + q**2)
    X = np.sqrt(sig**2 + q**2)
    ytil = eta * cosd + q * sind
    dtil = eta * sind - q * cosd
    
    Rdtil = R + dtil
    Rsig = R + sig
    Reta = R + eta
    RX = R + X
    
    lnRdtil = np.log(Rdtil)
    lnReta = np.log(Reta)
    lnReta0= -np.log(R - eta)
    ORRsig = 1 / (R * Rsig)
    OReta = 1 / Reta
    ORReta = 1 / (R * Reta)
    
    # Check for 'bad' values
    epsn=1e-15 # numerical 'zero' 
    indfix = (np.abs(Reta) < epsn)
    #indfix=np.flatnonzero(abs(Reta) < epsn)
    #if (not  (0 in indfix.shape)):
    if indfix.any():
        lnReta[indfix] = lnReta0[indfix]
        OReta[indfix] = 0 
        ORReta[indfix] = 0 
    
    #indfix=np.flatnonzero(abs(Rsig) < epsn)
    indfix = (np.abs(Rsig) < epsn)
    if indfix.any():
        #ORsig[indfix] = 0 
        ORRsig[indfix] = 0 
    
    
    # theta term with q = 0 fix
    # NOTE: probably could clean this seciton up...
    '''
    %betatop=sig.*eta;
    %betabottom=q.*R;
    %nz=find(betabottom~=0);
    %theta=pi/2*sign(betatop);
    %theta(nz)=atan(betatop(nz)./betabottom(nz));
    %theta(find(abs(q) > epsn))  = atan((sig.*eta)./(q.*R));
    '''
    theta = np.zeros_like(sig)
    #indfix=np.flatnonzero(abs(q) <= epsn)
    indfix = (np.abs(q) <= epsn)
    if indfix.any():
        theta[indfix] = 0 
        #indfix=np.flatnonzero(abs(q) > epsn)
        indfix = (np.abs(q) > epsn)
        theta[indfix] = np.arctan( (sig[indfix] * eta[indfix]) / (q[indfix] * R[indfix]) )
    else:
        theta = np.arctan((sig * eta) / (q * R))
    
    
    # The I_12345 factors
    if np.abs(cosd) < epsn: # 90 degree dipping plane (e.g. perfec strike-strip fault)
        I5 = -a * sig * sind / Rdtil
        I4 = -a * q / Rdtil
        I3 = a/2.0 * (eta / Rdtil + (ytil * q) / (Rdtil**2) - lnReta)
        I2 = -a * lnReta - I3
        I1 = -a/2.0 * (sig * q) / (Rdtil**2)
    
    else:
        # default [eqn. (28)]
        #   sigtemp(indfix) = epsn;
        #  I5 = a * 2 ./ cosd .* atan2( (eta.*(X+q.*cosd) + X.*RX.*sind),...
        #                             (sig.*RX.*cosd) );
        I5 = a*2.0 / cosd * np.arctan( (eta * (X + q * cosd) + X * RX * sind) / (sig * RX * cosd) )
        indfix = (np.abs(sig) < epsn)
        if indfix.any():
            I5[indfix] = 0
        I4 = a / cosd * (lnRdtil - sind * lnReta)
        I3 = a * (1 / cosd * ytil / Rdtil - lnReta) + tand * I4
        I2 = -a * lnReta - I3
        I1 = -a / cosd * sig / Rdtil - tand * I5
        
    
    # Fault-specific parameters
    if fault_type == 1: # Strike-Slip
        f1 = (sig * q) * ORReta + theta + I1 * sind
        f2 = (ytil * q) * ORReta + (q * cosd) * OReta + I2 * sind
        f3 = (dtil * q) * ORReta + (q * sind) * OReta + I4 * sind
    
    elif fault_type == 2: # Dip Slip
        f1 = q / R - I3 * cssnd
        f2 = (ytil * q) * ORRsig + cosd * theta - I1 * cssnd
        f3 = (dtil * q) * ORRsig + sind * theta - I5 * cssnd
    
    elif fault_type == 3: # Tensile/Dike
        f1 = q ** 2 * ORReta - I3 * sind2
        f2 = (-dtil * q) * ORRsig - sind * ((sig * q) * ORReta - theta) - I1 * sind2
        f3 = (ytil * q) * ORRsig + cosd * ((sig * q) * ORReta - theta) - I5 * sind2
    
    return f1,f2,f3




def calc_okada(U,x,y,nu,delta,d,length,W,fault_type,strike,tp):
    '''
    Okada fault model for dislocation in an elastic half-space.
    based on BSSA Vol. 95 p.1135-45, 1985
    Adapted from: http://sioviz.ucsd.edu/~fialko/software.html
    
    Inputs:
    % U is slip, NOTE: (-) for dextral, normal faults, and dyke opening
    % x,y are the observation points (m)
    % d is depth (m, to top of fault, positive down)
    % nu is Poisson ratio (unitless)
    % delta is dip angle (degrees from horizontal, 90=vertical)
    % strike is strike (degrees counterclockwise from North, 0=N-S)
    % len,W are the fault length and width (m)
    % fault_type is 1 2 3 for strike, dip, and opening
    % tp is the optional topo vector (size(x))
    
    # NOTE: solution highly variable at dip ~90
    '''
    pi = np.pi
    delta = np.deg2rad(delta)
    strike = np.deg2rad(strike)
    
    # define parameters with respect to the BOTTOM of the fault (assume
    # that the input ones correspond to the TOP)
    cosd = np.cos(delta)
    sind = np.sin(delta)
    d = d + W * sind
    x = x - W * cosd * np.cos(strike)
    y = y + W * cosd * np.sin(strike)
    d = d + tp
    strike = -strike + pi/2
    coss = np.cos(strike)
    sins = np.sin(strike)
    
    #rot = np.array([coss,- sins,sins,coss]).reshape(1,-1) #may not be correct...
    #rot = np.array([coss, -sins, sins, coss]) #not used
    rotx = x * coss + y * sins
    roty = -x * sins + y * coss
    
    # Okada fault model for dislocation in an elastic half-space.
    #  based on BSSA Vol. 95 p.1135-45, 1985
    L = length/2
    Const = -U/(2*pi)
    
    p = roty * cosd + d * sind # a matrix eqn. (30)
    q = roty * sind - d * cosd # a matrix eqn. (30)
    a = 1 - 2 * nu #mu/(lambda+mu) = 1-2*poisson's ratio
    
    parvec = np.array([a,delta,fault_type])
    f1a,f2a,f3a = fBi(rotx+L, p, parvec, p, q)
    f1b,f2b,f3b = fBi(rotx+L, p-W, parvec, p, q)
    f1c,f2c,f3c = fBi(rotx-L, p, parvec, p, q)
    f1d,f2d,f3d = fBi(rotx-L, p-W, parvec, p, q)
    
    # Diagnositic plots
    #rp.plot.side_by_side_old(f2a,f2b,f2c, False)
    #rp.plot.side_by_side_old(f1a,f2a,f3a, False)
    #rp.plot.side_by_side_old(f1b,f2b,f3b, False)
    #rp.plot.side_by_side_old(f1c,f2c,f3c, False)
    #rp.plot.side_by_side_old(f1d,f2d,f3d, False)

    
    # Displacement eqns. (25-27)
    uxj = Const * (f1a - f1b - f1c + f1d)
    uyj = Const * (f2a - f2b - f2c + f2d)
    uz = Const * (f3a - f3b - f3c + f3d)
    
    # rotate horizontals back to the orig. coordinate system
    ux = -uyj * sins + uxj * coss
    uy = uxj * sins + uyj * coss
    # HF is scaling factor for anisotropy
    #ux = HF * (-uyj * sins + uxj * coss)
    #uy = HF * (uxj * sins + uyj * coss)
    
    return ux,uy,uz


def calc_okada_multimode(U,x,y,nu,delta,d,length,wid,strike,tp):
    '''
    Linear superposition of U = np.array([dip-slip, strike-slip, and tensile displacement])
    '''
    u_ss, u_ds, u_t = U
    ux,uy,uz = calc_okada(u_ss,x,y,nu,delta,d,length,wid,1,strike,tp)
    ux1,uy1,uz1 = calc_okada(u_ds,x,y,nu,delta,d,length,wid,2,strike,tp)
    ux2,uy2,uz2 = calc_okada(u_t,x,y,nu,delta,d,length,wid,3,strike,tp)
    
    UX = ux + ux1 + ux2
    UY = uy + uy1 + uy2
    UZ = uz + uz1 + uz2
    
    return UX,UY,UZ


def benchmark(inc=23.0, ald=-77.0, wavelength=5.66):
    ''' Make sure python output matches matlab output (from Yuri Fialko's SIC)'''   
    # Grid origin and resolution
    xx = np.linspace(-100,100,201)*1e3 #Note 201 critical because includes exactly 0
    yy = np.linspace(-100,100,201)*1e3
    x,y = np.meshgrid(xx,yy)
    
    # Strike-Slip Example
    xcen=0
    ycen=0
    U = 1.0 # [m] U is slip
    # x,y are the observation points
    d = 1e-3 #[m] # d is depth (positive down)
    nu = 0.27 # nu is Poisson ratio
    delta = 89.99 # [degrees] delta is dip angle, 90.0 exactly might cause numerical issues?
    strike = 90.0 # [degrees] counter clockwise from north
    length = 70e3 #[m] # len,W are the fault length and width, resp.
    width = 15e3 #[m]
    fault_type = 1 # fault_type is 1 2 3 for strike, dip, and opening
    tp = np.zeros_like(x) # tp is the optional topo vector (size(x))
    
    # Run the model
    #calc_okada(U,x,y,nu,delta,d,length,W,fault_type,strike,tp)
    ux,uy,uz = calc_okada(U,x,y,nu,delta,d,length,width,fault_type,strike,tp)  
    
    data = np.dstack([ux, uy, uz])
    cart2los = get_cart2los(inc,ald)
    los = np.sum(data * cart2los, axis=2)
    
    # Create dictionary of parameters for plotting routine
    params=dict(xcen=xcen,ycen=ycen,U=U,d=d,nu=nu,delta=delta,strike=strike,length=length,width=width,fault_type=fault_type,inc=inc,ald=ald,wavelength=wavelength)
    plot_components(x,y,ux,uy,uz,los,params)
    plot_los(x,y,ux,uy,uz,los,params)
    plot_profile(100,ux,uy,uz,los)
    
    #return ux,uy,uz
    #return np.array([ux,uy,uz])

def get_cart2los(inc,ald,x):
        # converted to LOS
    #los = data.dot(cart2los) * 1e2 # maybe use numpy.tensordot? not sure...
    # For now fake it
    look = np.deg2rad(inc) * np.ones_like(x) # incidence
    head = np.deg2rad(ald) * np.ones_like(x) #heading (degreees clockwise from north)
    # NOTE: matlab code default is -167 'clockwise from north' (same as hannsen text fig 5.1)
    # This is for descending envisat beam 2, asizmuth look direction (ALD) is perpendicular to heading (-77)
    
    # however, make_los.pl generates unw file with [Incidence, ALD], ALD for ascending data is 77
    # make_los.pl defines "(alpha) azimuth pointing of s/c" 
    EW2los = np.sin(head) * np.sin(look)
    NS2los = np.cos(head) * np.sin(look) 
    Z2los = -np.cos(look)
    cart2los = -np.dstack([EW2los, NS2los, Z2los]) #NOTE: negative here implies uplift=positive in LOS
    
    return cart2los
    

def tinker(example,inc=23.0, ald=-77.0, wavelength=5.66):
    ''' Check various fault types and orientations
    
    example can be one of 'strike slip', 'thrust', 'normal', 'dyke intrusion', 'inflating sill'
    
    NOTE: that negative LOS --> uplift in this convention
    '''   
    # Grid origin and resolution
    xx = np.linspace(-100,100,201)*1e3 #Note 201 critical because includes exactly 0
    yy = np.linspace(-100,100,201)*1e3
    x,y = np.meshgrid(xx,yy)
    tp = np.zeros_like(x)
    
    # Load variables from file -> note either have to use namespace access or explicit import
    #import defaults
    #defaults.length
    #from defaults import U,nu,delta,d,length,width,fault_type,strike,xcen,ycen
    # but has to be in same directory... :(
    # NOTE: a thrid option is to write a simple routine to parse input w/ = chars
    xcen,ycen,U,d,nu,delta,strike,length,width,fault_type = examples.okada(example)
    
    # Create dictionary of parameters for plotting routine
    params=dict(xcen=xcen,ycen=ycen,U=U,d=d,nu=nu,delta=delta,strike=strike,length=length,width=width,fault_type=fault_type,inc=inc,ald=ald,wavelength=wavelength)
    
    # Run the model
    #calc_okada(U,x,y,nu,delta,d,length,W,fault_type,strike,tp)
    ux,uy,uz = calc_okada(U,x,y,nu,delta,d,length,width,fault_type,strike,tp)  
    
    data = np.dstack([ux, uy, uz])
    cart2los = get_cart2los(inc,ald,x)
    los = np.sum(data * cart2los, axis=2)
    
    plot_components(x,y,ux,uy,uz,los,params)
    plot_los(x,y,ux,uy,uz,los,params)
    plot_profile(100,ux,uy,uz,los)


def plot_fault(fig,strike=None,delta=None,length=None,width=None,xcen=None,ycen=None,**kwargs):
    ''' matlab way to project fault plane onto surface'''
    #XB = [] #lists for multiple faults in same domain 
    #YB = []
    
    # Project fault coordinates onto surface
    sins = np.sin(np.deg2rad(strike))
    coss = np.cos(np.deg2rad(strike))
    Lx = 0.5 * length * sins
    Ly = 0.5 * length * coss
    W = width * np.cos(np.deg2rad(delta))
    
    # Concatenate coordinates
    xb = np.array([-Lx+W*coss, -Lx, Lx, Lx+W*coss, -Lx+W*coss]) + xcen
    yb = np.array([-Ly-W*sins, -Ly, Ly, Ly-W*sins, -Ly-W*sins]) + ycen
    #XB.append(xb)
    #YB.append(yb)
    
    # scale for plotting
    xb = xb * 1e-3
    yb = yb * 1e-3
    
    # put it on the plots!
    for ax in fig.get_axes():
        ax.plot(xb,yb,'w-',lw=2)
 

def plot_los_indicator(ax,ald):
    ''' Add LOS arrow indicator in axes coordinates 
    Inputs: 
        ax     axes to add to
        ald    azimuth look direction (second array in geo_incidence
    '''
    L = 0.1
    x0,y0 = (0.8, 0.8)
    dx = L * np.cos( np.pi/2 - np.deg2rad(ald) )
    dy = L * np.sin( np.pi/2 - np.deg2rad(ald) )
    ax.arrow(x0,y0,dx,dy,transform=ax.transAxes, color='k') #add text too:
    ax.text(0.9,0.9,'LOS',ha='right',va='top',transform=ax.transAxes,fontweight='bold')
    #ax1.annotate('LOS', (x0,y0), xytext=(x0+dx,x0+dy), xycoords='axes fraction', textcoords='axes fraction', 
    #            arrowprops=dict(width=1,frac=0.3,headwidth=5,facecolor='black'), fontweight='bold') # NOTE: imshow origin has effect on this
       
                 
def plot_components(x,y,ux,uy,uz,los,params,profile=False):
    '''
    show components of deformation, along with projection into LOS
    NOTE: also would be cool to plot 3D surface!
    # just pass all parameters
    '''    
    # Convert to km and cm for ploting
    x,y = np.array([x,y]) * 1e-3
    ux,uy,uz,los = np.array([ux,uy,uz,los]) * 1e2
    
    # step size for quiver plot resampling
    nx = 20
    ny = 20
    
    fig, (ax,ax1,ax2) = plt.subplots(1,3, 
                                subplot_kw=dict(aspect=1.0, adjustable='box-forced'), 
                                sharex=True, sharey=True, figsize=(17,6)) #fig_kw
    
    extent = [x.min(), x.max(), y.min(), y.max()]
    #plt.locator_params(tight=True, nbins=4) #control number of easting/northing ticks
    #sc = ax.scatter(x_km,y_km,c=data,cmap=plt.cm.bwr) #colormap not centered on zero
    #norm = MidpointNormalize(midpoint=0)
    #sc = ax.scatter(x_km,y_km,c=data,cmap=plt.cm.bwr,norm=norm)
    #im = ax.imshow(uz)
    #im = ax.pcolor(x,y,uz)
    im = ax.imshow(uz, extent=extent)
    #ax.quiver(x[::ny,::ny], y[::nx,::ny], ux[::nx,::ny], uy[::nx,::ny]) #vector sum - show in second figure
    ax.set_title('Vertical Displacement, Uz')
    ax.set_xlabel('EW Distance [km]')
    ax.set_ylabel('NS Distance [km]')
    cb = plt.colorbar(im, ax=ax, orientation='horizontal')#, pad=0.1) #ticks=MaxNLocator(nbins=5) #5 ticks only)
    cb.set_label('cm')
    
    # NOTE: look into code to see how error and wgt are determined..
    #sc1 = ax1.scatter(x_km,y_km,c=err,cmap=plt.cm.Reds)
    #im1 = ax1.imshow(ux)
    #im1 = ax1.pcolor(x,y,ux)
    im1 = ax1.imshow(ux, extent=extent)
    ax1.quiver(x[::ny,::ny], y[::nx,::ny], ux[::nx,::ny], np.zeros_like(uy)[::nx,::ny])
    ax1.set_title('EW Displacement, Ux')
    cb1 = plt.colorbar(im1, ax=ax1, orientation='horizontal')#, pad=0.1)
    cb1.set_label('cm')    
    
    #sc2 = ax2.scatter(x_km,y_km,c=wgt,cmap=plt.cm.Blues, norm=LogNorm())
    #cb2 = plt.colorbar(sc2, ax=ax2, orientation='horizontal', pad=0.1)
    #sc2 = ax2.scatter(x_km,y_km,c=wgt,cmap=plt.cm.Blues)
    #im2 = ax2.imshow(uy)
    #im2 = ax2.pcolor(x,y,uy)
    im2 = ax2.imshow(uy, extent=extent)
    ax2.quiver(x[::ny,::ny], y[::nx,::ny], np.zeros_like(ux)[::nx,::ny], uy[::nx,::ny])
    cb2 = plt.colorbar(im2, ax=ax2, orientation='horizontal')#, pad=0.1)
    ax2.set_title('NS Displacement, Uy')
    cb2.set_label('cm')
    
    plot_fault(fig,**params)
    
    plt.suptitle('Components of Deformation', fontsize=16, fontweight='bold')


def plot_los(x,y,ux,uy,uz,los,params,profile=False):
    ''' Separate figure showing displacement and Wrapped Phase in Radar     '''
    # Convert to km and cm for ploting
    x,y = np.array([x,y]) * 1e-3
    ux,uy,uz,los = np.array([ux,uy,uz,los]) * 1e2
    
    # extract a few varialbes from params dictionary
    inc = params['inc']
    ald = params['ald']
    wavelength = params['wavelength']
    
    # Set view
    nx=20
    ny=20
    extent = [x.min(), x.max(), y.min(), y.max()]
    
    # --------------
    fig, (ax,ax1,ax2) = plt.subplots(1,3,subplot_kw=dict(aspect=1.0, adjustable='box-forced'),sharex=True, sharey=True, figsize=(17,6))
    # vertical displacement w/ horizontal vectors # NOTE: add quiver scale arrow!
    im = ax.imshow(uz, extent=extent)
    ax.quiver(x[::ny,::ny], y[::nx,::ny], ux[::nx,::ny], uy[::nx,::ny])
    ax.set_title('Model Displacement Field')
    ax.set_xlabel('EW Distance [km]')
    ax.set_ylabel('NS Distance [km]')
    cb = plt.colorbar(im, ax=ax, orientation='horizontal', pad=0.1) #ticks=MaxNLocator(nbins=5) #5 ticks only)
    cb.set_label('cm')
    
    im = ax1.imshow(los, extent=extent)
    #ax1.quiver(x[::ny,::ny], y[::nx,::ny], ux[::nx,::ny], uy[::nx,::ny])
    plot_los_indicator(ax1,ald)
    ax1.set_title('LOS (inc,ald)=(%s,%s)' % (inc,ald) )
    cb = plt.colorbar(im, ax=ax1, orientation='horizontal', pad=0.1) #ticks=MaxNLocator(nbins=5) #5 ticks only)
    cb.set_label('cm')
    
    # wrapped LOS - think about why this works...
    los_wrapped = np.remainder(los - los.min(), wavelength/2.0) / (wavelength/2.0)
    im = ax2.imshow(los_wrapped, extent=extent, vmin=0, vmax=1)
    plot_los_indicator(ax2,ald)
    ax2.set_title('LOS Wrapped')
    cb = plt.colorbar(im, ax=ax2, orientation='horizontal', ticks=[], pad=0.1) #ticks=MaxNLocator(nbins=5) #5 ticks only)
    cb.set_label('{0} cm'.format(wavelength/2)) #1 color cycle = lambda/2
    
    plot_fault(fig,**params) 
    
    plt.suptitle('Model in Radar Line of Sight', fontsize=16, fontweight='bold')
    

def plot_profile(ind,ux,uy,uz,los,axis=0):
    ''' straight line profile through specified axis of ux,uy,uz,los'''
    # Show profile line in separate LOS plot
    plt.figure()
    plt.imshow(los)
    if axis == 0:
        plt.axhline(ind,color='k', lw=2)
        #plt.annotate('A',(ind,0))
    else:
        plt.vline(ind,color='k', lw=2)
    plt.title('Profile line')
    
    
    # Convert to km and cm for ploting
    #x,y = np.array([x,y]) * 1e-3
    ux,uy,uz,los = np.array([ux,uy,uz,los]) * 1e2
    
    if axis==1:
        ux,uy,uz,los = [x.T for x in [ux,uy,uz,los]]
        
    # extract profiles
    ux_p = ux[ind]
    uy_p = uy[ind]
    uz_p = uz[ind]
    los_p = los[ind]
    
    fig, (ax,ax1,ax2,ax3) = plt.subplots(1,4,sharex=True, sharey=True, figsize=(17,6))
    ax.plot(ux_p,'k.-',lw=2)
    ax.set_title('Ux')
    ax.set_ylabel('Displacement [cm]')
    ax.set_xlabel('Distance [km]')
    ax.text(0,0.9,'A',fontweight='bold',ma='center',transform=ax.transAxes)
    ax.text(0.9,0.9,'B',fontweight='bold',ma='center',transform=ax.transAxes)
    
    ax1.plot(uy_p,'k.-',lw=2)
    ax1.set_title('Uy')

    ax2.plot(uz_p,'k.-',lw=2)
    ax2.set_title('Uz')
    
    ax3.plot(los_p,'k.-',lw=2)
    ax3.set_title('LOS')
    
    for a in (ax,ax1,ax2,ax3):
        a.axhline(0,color='gray',linestyle='--')
        a.grid(True)
    
    #ratio of uz to ur
    # NOTE: just print max ratio
    print 'Ur/Uz = ', ux_p.max() / uz_p.max()
    '''
    plt.figure()
    plt.plot(uz_p/ux_p,'k.-',lw=2)
    plt.xlabel('Distance [km]')
    plt.ylabel('Uz/Ur Ratio')
    plt.title('Vertical vs. Horizontal Displacements')
    plt.show()
    '''

if __name__ == '__main__':
    # Benchmark matching matlab demo.m
    print 'Functions intended for use within roipy. Here is a benchmark'
    ux,uy,uz = benchmark()



