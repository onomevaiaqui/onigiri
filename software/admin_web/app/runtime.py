"""Bounded ROS session and local RPC queue, independent of the web virtualenv."""
import json,os,signal,subprocess,tempfile,threading,time,uuid
from pathlib import Path

class Process:
    def __init__(self,worker,enabled=False):
        self.worker=Path(worker);self.enabled=enabled;self.process=None;self.directory=None;self.lock=threading.RLock();self.log=None
    def start(self,*args):
        with self.lock:
            if not self.enabled:raise ValueError('Integração ROS desabilitada neste servidor')
            if self.process and self.process.poll() is None:return self.status()
            self.stop();self.directory=tempfile.TemporaryDirectory(prefix='onigiri-session-');root=Path(self.directory.name)
            self.log=(root/'worker.log').open('ab')
            try:self.process=subprocess.Popen(['bash',str(self.worker),str(root),*map(str,args)],stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True)
            except Exception:self.stop();raise
            return self.status()
    def stop(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                for sig,timeout in ((signal.SIGINT,5),(signal.SIGTERM,2),(signal.SIGKILL,2)):
                    try:os.killpg(self.process.pid,sig)
                    except ProcessLookupError:break
                    try:self.process.wait(timeout=timeout);break
                    except subprocess.TimeoutExpired:pass
            self.process=None
            if self.log:self.log.close();self.log=None
            if self.directory:self.directory.cleanup();self.directory=None
            return self.status()
    def status(self):
        with self.lock:
            running=self.process is not None and self.process.poll() is None
            result={'enabled':self.enabled,'running':running,'state':'running' if running else 'failed' if self.process else 'idle'}
            if self.directory:
                root=Path(self.directory.name)
                try:result['telemetry']=json.loads((root/'status.json').read_text())
                except (OSError,ValueError):pass
                try:
                    with (root/'worker.log').open('rb') as stream:
                        stream.seek(0,2);stream.seek(max(0,stream.tell()-4000));result['log_tail']=stream.read().decode(errors='replace')
                except OSError:pass
            return result
    def send(self,operation,**data):
        with self.lock:
            if not self.process or self.process.poll() is not None or not self.directory:raise ValueError('Conecte o ROS no painel primeiro')
            root=Path(self.directory.name);paths=list(root.glob('request-*.json'))
            if len(paths)>=16:raise ValueError('Fila ROS ocupada')
            identifier=uuid.uuid4().hex;temp=root/(identifier+'.tmp')
            temp.write_text(json.dumps({'id':identifier,'created_at':time.time(),'operation':operation,**data}));temp.rename(root/('request-'+str(time.time_ns())+'-'+identifier+'.json'))
            return {'queued':True,'id':identifier}
