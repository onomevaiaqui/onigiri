"""Local map library and opt-in ROS SLAM process. Never publishes motion commands."""
from __future__ import annotations

import base64
import json
import os
import re
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path


class MapManager:
    def __init__(self, root: Path, worker: Path, enabled: bool = False):
        self.root = root
        self.worker = worker
        self.enabled = enabled
        self.process = None
        self.lock = threading.RLock()
        self.log = None
        self.experimental = False
        self.stationary = False
        self.lidar_odometry = False
        self.rgbd = False
        self.rgbd_session = None
        self.rgbd_enabled = os.environ.get("ONIGIRI_RGBD_ENABLED")=="1"
        self.lidar_enabled = os.environ.get('ONIGIRI_LIDAR_ODOMETRY_ENABLED') == '1'
        self.preview_process = None
        self.preview_directory = None

    @staticmethod
    def valid_name(name: str) -> str:
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,59}', name):
            raise ValueError('Use até 60 letras sem acentos, números, hífen ou sublinhado no nome.')
        return name

    def status(self) -> dict:
        with self.lock:
            code = self.process.poll() if self.process else None
            running = self.process is not None and code is None
            if self.process is not None and code is not None:
                self._stop_preview()
            return {'enabled': self.enabled, 'running': running,
                    'lidar_odometry_enabled': self.lidar_enabled, 'rgbd_enabled':self.rgbd_enabled,
                    'profile': self.profile(),
                    'state': 'running' if running else 'failed' if code not in (None, 0) else 'idle',
                    'detail': ('Mapeamento visual RGB-D pela Gemini 2. Aguarde odometria e mapa.' if running and self.rgbd else 'Odometria pelo LiDAR ativa. Perfil experimental de mapeamento do sensor, sem navegação.' if running and self.lidar_odometry else
                               'Teste parado: TF fixas aproximadas. Mantenha o robô imóvel; não use este mapa para navegação.' if running and self.stationary else
                               'SLAM experimental com parâmetros padrão. Não validado para navegação; TF e odometria precisam estar disponíveis.' if running and self.experimental else
                               'SLAM iniciado; a captura depende do LiDAR, TF e odometria. Salvar confirma se há mapa disponível.' if running else
                               'SLAM encerrou com erro. Consulte data/maps/slam.log.' if code not in (None, 0) else
                               'Pronto para iniciar o SLAM.' if self.enabled else
                               'Captura ROS não habilitada neste servidor. Você pode carregar e guardar mapas locais.')}

    def profile(self):
        return 'rgbd' if self.rgbd else 'lidar-odometry' if self.lidar_odometry else 'stationary-preview' if self.stationary else 'experimental-default' if self.experimental else 'configured'

    def start(self, experimental: bool = False, stationary: bool = False, lidar_odometry: bool = False, rgbd: bool = False) -> dict:
        with self.lock:
            if not self.enabled:
                raise ValueError('Captura ROS não habilitada neste servidor.')
            if rgbd and (stationary or lidar_odometry):raise ValueError('O perfil RGB-D não usa TF de teste nem RF2O')
            if rgbd and not self.rgbd_enabled:raise ValueError('Instale a integração RGB-D no Raspberry antes de iniciar')
            if lidar_odometry and stationary:
                raise ValueError('Escolha Teste parado ou Odometria pelo LiDAR; não podem operar juntos.')
            if lidar_odometry and not self.lidar_enabled:
                raise ValueError('Instale e habilite RF2O no Raspberry antes de usar odometria pelo LiDAR.')
            if self.process and self.process.poll() is None:
                return self.status()
            params = os.environ.get('ONIGIRI_SLAM_PARAMS', '')
            if not (rgbd or experimental or stationary or lidar_odometry) and (not params or not Path(params).is_file()):
                raise ValueError('Configure ONIGIRI_SLAM_PARAMS com o YAML de SLAM validado para este robô.')
            self.root.mkdir(parents=True, exist_ok=True)
            if self.log:
                self.log.close()
            self.log = (self.root / 'slam.log').open('ab')
            self.rgbd = rgbd
            if self.rgbd_session:self.rgbd_session.cleanup();self.rgbd_session=None
            if rgbd:self.rgbd_session=tempfile.TemporaryDirectory(prefix=".rgbd-",dir=self.root)
            self.stationary = stationary
            self.lidar_odometry = lidar_odometry
            self.experimental = experimental or stationary or lidar_odometry
            operation = 'start-lidar-odometry' if lidar_odometry else 'start-stationary' if stationary else 'start-experimental' if experimental else 'start'
            command=['bash',str(self.worker),'start-rgbd',str(Path(self.rgbd_session.name)/'rtabmap.db')] if rgbd else ['bash',str(self.worker),operation]
            self.process = subprocess.Popen(command, stdout=self.log,
                                            stderr=subprocess.STDOUT, start_new_session=True)
            self._stop_preview()
            self.preview_directory = tempfile.TemporaryDirectory(prefix='.preview-', dir=self.root)
            try:
                self.preview_process = subprocess.Popen(['bash', str(self.worker), 'preview',
                    str(Path(self.preview_directory.name) / 'snapshot.json')], stdout=self.log,
                    stderr=subprocess.STDOUT, start_new_session=True)
            except OSError:
                self.stop()
                raise
            return self.status()

    @staticmethod
    def _terminate(process):
        if process and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=3)

    def _stop_preview(self):
        self._terminate(self.preview_process)
        self.preview_process = None
        if self.preview_directory:
            self.preview_directory.cleanup()
            self.preview_directory = None

    def preview(self, after=None):
        # No lock across a slow map save; snapshots are published atomically.
        if not self.enabled:
            return {'state': 'disabled', 'detail': 'Prévia disponível no Raspberry com captura ROS habilitada.'}
        if self.process is None or self.process.poll() is not None:
            return {'state': 'idle', 'detail': 'Inicie o mapeamento para acompanhar a prévia.'}
        directory = self.preview_directory
        if not directory:
            return {'state': 'waiting', 'detail': 'Preparando a leitura do mapa.'}
        try:
            snapshot = json.loads((Path(directory.name) / 'snapshot.json').read_text())
        except (OSError, ValueError):
            failed = self.preview_process is not None and self.preview_process.poll() is not None
            return {'state': 'error' if failed else 'waiting', 'detail':
                    'Leitor da prévia indisponível. Consulte slam.log.' if failed else
                    'Aguardando /map. Verifique RGB, profundidade alinhada, câmera e odometria visual.' if self.rgbd else 'Aguardando /map. Verifique LiDAR, SLAM e transformações TF.'}
        if 'error' in snapshot:
            return {'state': 'error', 'detail': snapshot['error']}
        if after is not None and snapshot.get('changed_at', snapshot['received_at']) == after:
            snapshot.pop('png_base64', None)
        age = max(0, time.time() - snapshot['received_at'])
        return {**snapshot, 'state': 'stale' if age > 15 else 'live', 'age_seconds': round(age, 1),
                'changed_age_seconds': round(max(0, time.time() - snapshot.get('changed_at', snapshot['received_at'])), 1),
                'detail': 'Sem atualização recente do mapa.' if age > 15 else 'Recebendo mapa do SLAM.'}

    def stop(self) -> dict:
        with self.lock:
            self._stop_preview()
            if self.process and self.process.poll() is None:
                os.killpg(self.process.pid, signal.SIGINT)
                try:
                    self.process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(self.process.pid, signal.SIGTERM)
                    try:
                        self.process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(self.process.pid, signal.SIGKILL)
                        self.process.wait(timeout=3)
            self.process = None
            if self.rgbd_session:self.rgbd_session.cleanup();self.rgbd_session=None
            if self.log:
                self.log.close()
                self.log = None
            return self.status()

    def list(self) -> list[dict]:
        if not self.root.exists():
            return []
        maps = []
        for path in sorted(self.root.iterdir()):
            if path.is_dir() and not path.name.startswith('.') and (path / 'map.yaml').is_file() and (path / 'map.pgm').is_file():
                metadata = self.metadata(path)
                entry = {'name': path.name, 'source': metadata.get('source', 'local')}
                if 'profile' in metadata:
                    entry['profile'] = metadata['profile']
                maps.append(entry)
        return maps

    @staticmethod
    def metadata(path: Path) -> dict:
        try:
            return json.loads((path / 'metadata.json').read_text())
        except (OSError, ValueError):
            return {}

    def read(self, name: str) -> dict:
        path = self.root / self.valid_name(name)
        if not (path / 'map.yaml').is_file() or not (path / 'map.pgm').is_file():
            raise FileNotFoundError('Mapa não encontrado.')
        return {'name': name, 'profile': self.metadata(path).get('profile'), 'yaml': (path / 'map.yaml').read_text(),
                'pgm_base64': base64.b64encode((path / 'map.pgm').read_bytes()).decode()}

    def save(self, name: str, yaml: str | None = None, pgm_base64: str | None = None) -> dict:
        with self.lock:
            name = self.valid_name(name)
            self.root.mkdir(parents=True, exist_ok=True)
            final = self.root / name
            if final.exists():
                raise FileExistsError('Já existe um mapa com esse nome. Escolha outro nome.')
            with tempfile.TemporaryDirectory(prefix='.saving-', dir=self.root) as temporary:
                stage = Path(temporary)
                if yaml is None:
                    if not self.enabled or not self.status()['running']:
                        raise ValueError('Inicie o mapeamento ROS antes de salvar a captura.')
                    try:
                        command=['bash',str(self.worker),'save-rgbd',str(stage/'map'),str(Path(self.rgbd_session.name)/'rtabmap.db')] if self.rgbd else ['bash', str(self.worker), 'save', str(stage / 'map')]
                        saver = subprocess.Popen(command,
                                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                                 start_new_session=True)
                        saver.wait(timeout=35)
                    except subprocess.TimeoutExpired as error:
                        os.killpg(saver.pid, signal.SIGKILL)
                        saver.wait(timeout=3)
                        raise ValueError('Tempo esgotado ao salvar. Verifique se o SLAM publica /map.') from error
                    if saver.returncode:
                        raise ValueError('O ROS não conseguiu salvar /map. Verifique o SLAM, o LiDAR e as transformações TF.')
                    source = 'ros'
                else:
                    try:
                        image = base64.b64decode(pgm_base64 or '', validate=True)
                    except ValueError as error:
                        raise ValueError('Imagem PGM inválida.') from error
                    if not image.startswith((b'P2', b'P5')) or len(image) > 12_000_000:
                        raise ValueError('Use um arquivo PGM de até 12 MB.')
                    if len(yaml) > 100_000 or not re.search(r'^\s*resolution\s*:', yaml, re.M) or not re.search(r'^\s*origin\s*:', yaml, re.M):
                        raise ValueError('YAML de mapa inválido.')
                    (stage / 'map.yaml').write_text(yaml)
                    (stage / 'map.pgm').write_bytes(image)
                    source = 'imported'
                if not (stage / 'map.yaml').is_file() or not (stage / 'map.pgm').is_file():
                    raise ValueError('O salvamento não produziu o par YAML/PGM.')
                # Keep the image reference portable after the staging directory is renamed.
                text = (stage / 'map.yaml').read_text()
                text = re.sub(r'^\s*image\s*:.*$', 'image: map.pgm', text, flags=re.M)
                if not re.search(r'^image:', text, re.M):
                    text = 'image: map.pgm\n' + text
                (stage / 'map.yaml').write_text(text)
                metadata = {'source': source}
                if source == 'ros':
                    metadata['profile'] = self.profile()
                    if self.rgbd and not (stage/'rtabmap.db').is_file():raise ValueError('O salvamento visual não produziu o banco de localização')
                (stage / 'metadata.json').write_text(json.dumps(metadata))
                stage.rename(final)
            return {'name': name, 'source': source}
