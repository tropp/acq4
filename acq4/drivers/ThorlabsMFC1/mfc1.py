"""
Thorlabs MFC1 : microscope focus controller based on Trinamic TMCM-140-42-SE
and PDx-140-42-SE.


Hardware notes:

* Although the controller supports up to 64 microsteps per full step, the
  actual microstep size is not constant and becomes very nonlinear at around 
  16 microsteps. Using mixed_decay_threshold=-1 helps somewhat.

* Stall detection only works for a limited range of current + speed + threshold


"""
from .tmcm import TMCM140

class MFC1(object):
    def __init__(self, port, baudrate=9600):
        self.mcm = TMCM140(port, baudrate)
        self.mcm.stop()
        self.mcm.set_params(
            maximum_current=10,
            standby_current=0,
            mixed_decay_threshold=-1,
        )
        self.setResolution(16)
        
    def setResolution(self, res):
        """Set the microstep resolution of the motor.
        
        Must be 1, 2, 4, 8, 16, 32, or 64. Note that higher values have highly 
        irregular step sizes, but may result in smoother rotation.
        """
        assert res in 2**np.arange(7)
        res = int(np.log2(res))
        
        self.mcm.set_params(
            microstep_resolution=res,
            encoder_prescaler=int(100 * 2**res)
        )
        
    def position(self):
        """Return the current encoder position.
        """
        return self.mcm['encoder_position']
    
    def move(self, position, block=False):
        """Move to the requested position.
        
        If block is False, then return an object that may be used to check 
        whether the move is complete.
        """
        
        