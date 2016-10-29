"""
This module implements ddeint, a simple Differential Delay Equation
solver built on top of Scipy's odeint """

# REQUIRES Numpy and Scipy.
import numpy as np
import scipy.integrate
import scipy.interpolate


class ddeVar:
    """
    The instances of this class are special function-like
    variables which store their past values in an interpolator and
    can be called for any past time: Y(t), Y(t-d).
    Very convenient for the integration of DDEs.
    """

    def __init__(self,g,tc=0, Y0=None):
        """ g(t) = expression of Y(t) for t<tc """

        self.g = g
        self.tc= tc
        if Y0 is None:
            Y0 = self.g(tc)
        # We must fill the interpolator with 2 points minimum
        self.itpr = scipy.interpolate.interp1d(
            np.array([tc-1,tc-1.0E-10,tc]), # X
            np.array([self.g(tc-1), self.g(tc-1.0E-10), Y0]).T, # Y
            kind='linear', bounds_error=False,
            fill_value = self.g(tc))

    def update(self,t,Y):
        """ Add one new (ti,yi) to the interpolator """

        self.itpr.x = np.hstack([self.itpr.x, [t]])
        if Y.size == 1:
            self.itpr.y = np.hstack([self.itpr.y, Y])
        else:
            Y2 = np.array([Y], ndmin=2)
            self.itpr._y = np.vstack([self.itpr._y, Y2])
        self.itpr.fill_value = Y

    def __call__(self,t=0):
        """ Y(t) will return the instance's value at time t """

        return (self.g(t) if (t<self.tc) else self.itpr(t))



class dde(scipy.integrate.ode):
    """
    This class overwrites a few functions of ``scipy.integrate.ode``
    to allow for updates of the pseudo-variable Y between each
    integration step.
    """

    def __init__(self,f,jac=None):

        def f2(t,y,args):
            return f(self.Y,t,*args)
        scipy.integrate.ode.__init__(self,f2,jac)
        self.set_f_params(None)

    def integrate(self, t, step=0, relax=0):

        scipy.integrate.ode.integrate(self,t,step,relax)
        self.Y.update(self.t,self.y)
        return self.y

    def set_initial_value(self,Y):

        self.Y = Y #!!! Y will be modified during integration
        y0 = Y(Y.tc)
        if isinstance(y0, np.ndarray) and np.ndim(y0)==0:
            y0 = y0.item() # set_initial_value doesn't accept 0-dim array
        scipy.integrate.ode.set_initial_value(self, y0, Y.tc)

def ddeint(func,g,tt,fargs=None, Y0=None, with_model=False):
    """ Solves Delay Differential Equations

    Similar to scipy.integrate.odeint. Solves a Delay differential
    Equation system (DDE) defined by

        Y(t) = g(t) for t<0
        Y'(t) = func(Y,t) for t>= 0

    Where func can involve past values of Y, like Y(t-d).
    

    Parameters
    -----------
    
    func
      a function Y,t,args -> Y'(t), where args is optional.
      The variable Y is an instance of class ddeVar, which means that
      it is called like a function: Y(t), Y(t-d), etc. Y(t) returns
      either a number or a numpy array (for multivariate systems).

    g
      The 'history function'. A function g(t)=Y(t) for t<0, g(t)
      returns either a number or a numpy array (for multivariate
      systems).
    
    tt
      The vector of times [t0, t1, ...] at which the system must
      be solved.

    fargs
      Additional arguments to be passed to parameter ``func``, if any.

    Y0
      Initial values of the system at t=t0, if they are not g(t0).
    
    with_model
      An option to return the interpolator of the result to calculate values out of the argument `tt`

    Examples
    ---------
    
    We will solve the delayed Lotka-Volterra system defined as
    
        For t < 0:
        x(t) = 1+t
        y(t) = 2-t
    
        For t >= 0:
        dx/dt =  0.5* ( 1- y(t-d) )
        dy/dt = -0.5* ( 1- x(t-d) )
    
    The delay ``d`` is a tunable parameter of the model.

    >>> import numpy as np
    >>> from ddeint import ddeint
    >>> 
    >>> def model(XY,t,d):
    >>>     x, y = XY(t)
    >>>     xd, yd = XY(t-d)
    >>>     return np.array([0.5*x*(1-yd), -0.5*y*(1-xd)])
    >>> 
    >>> g = lambda t : np.array([1+t,2-t]) # 'history' at t<0
    >>> tt = np.linspace(0,30,20000) # times for integration
    >>> d = 0.5 # set parameter d 
    >>> yy = ddeint(model,g,tt,fargs=(d,)) # solve the DDE !
     
    """

    dde_ = dde(func)
    dde_.set_initial_value(ddeVar(g,tt[0],Y0))
    dde_.set_f_params(fargs if fargs else [])
    results = [dde_.integrate(dde_.t + dt) for dt in np.diff(tt)]
    if with_model:
        return [np.array( [g(tt[0])] + results), dde_.Y]
    else:
        return np.array( [g(tt[0])] + results)
