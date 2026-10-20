"""Body-to-wheel kinematics and leased motor commands; no ROS dependencies."""
import math
import time

def finite(*values):
    if not all(math.isfinite(v) for v in values):raise ValueError("Valores não finitos")

def wheels(chassis, vx, vy, wz, width, length):
    finite(vx,vy,wz,width,length)
    if width<=0 or length<=0:raise ValueError("Dimensões devem ser positivas")
    if chassis in ("tank","independent"):
        if abs(vy)>1e-6:raise ValueError("Este chassi não permite deslocamento lateral")
        left,right=vx-wz*width/2,vx+wz*width/2
        return [left,right] if chassis=="tank" else [left,right,left,right]
    if chassis=="mecanum":
        k=(width+length)/2
        return [vx-vy-k*wz,vx+vy+k*wz,vx+vy-k*wz,vx-vy+k*wz]
    raise ValueError("O perfil original mantém seu driver existente")

class DriveController:
    def __init__(self, sink, config, clock=time.monotonic):
        self.sink=sink;self.config=config;self.clock=clock;self.armed=False
        self.estop=False;self.last_command=None;self.arm_time=None
    def arm(self):
        if self.estop:raise ValueError("Parada latched: libere e rearme")
        self.armed=True;self.arm_time=self.clock();self.last_command=None
    def stop(self, emergency=False):
        self.armed=False;self.last_command=None
        if emergency:self.estop=True
        self.sink.stop()
    def release(self):
        self.armed=False;self.estop=False;self.sink.stop()
    def command(self,vx,vy,wz):
        if not self.armed or self.estop:return False
        try:
            values=wheels(self.config['chassis'],vx,vy,wz,self.config['track_separation_m'],self.config['wheelbase_m'])
            maximum=self.config['max_track_speed_mps']
            if maximum<=0:raise ValueError("Velocidade máxima inválida")
            scale=max(maximum,max(abs(x) for x in values))
            powers=[x/scale*self.config['power_limit']*(-1 if inv else 1) for x,inv in zip(values,self.config['motor_inversions'],strict=True)]
            self.sink.write(powers);self.last_command=self.clock();return True
        except Exception:
            self.stop(emergency=True);raise
    def tick(self):
        reference=self.last_command if self.last_command is not None else self.arm_time
        if self.armed and reference is not None and self.clock()-reference>(self.config.get('command_timeout_s',.3) if self.last_command is not None else 10.0):
            self.stop()
