import importlib.util,sqlite3,tempfile,unittest,tarfile,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'deploy/scripts'/ (name+'.py'));value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

class ProvisionTests(unittest.TestCase):
    def test_cloud_init_ssh_key_and_no_motion(self):
        config=module('build_sd_image').cloud_config('ssh-ed25519 AAAATEST local')
        self.assertFalse(config['ssh_pwauth'])
        self.assertTrue(config['users'][0]['lock_passwd'])
        self.assertEqual(config['users'][0]['name'],'onigiri')
        with self.assertRaises(ValueError):module('build_sd_image').cloud_config('bad key')
    def test_backup_sqlite_and_restore(self):
        tool=module('user_data')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'robot';(root/'data').mkdir(parents=True)
            with sqlite3.connect(root/'data/test.db') as db:db.execute('create table test (value)');db.execute('insert into test values (42)')
            (root/'data/platform.json').write_text('{"chassis":"tank"}')
            archive=Path(folder)/'backup.tar.gz';tool.backup(root,archive)
            (root/'data/platform.json').write_text('{}');tool.restore(root,archive)
            self.assertEqual((root/'data/platform.json').read_text(),'{"chassis":"tank"}')
            with sqlite3.connect(root/'data/test.db') as db:self.assertEqual(db.execute('select value from test').fetchone()[0],42)
            malicious=Path(folder)/'bad.tar.gz'
            with tarfile.open(malicious,'w:gz') as tar:
                item=tarfile.TarInfo('../escape');item.size=1;tar.addfile(item,io.BytesIO(b'x'))
            with self.assertRaises(ValueError):tool.restore(root,malicious)

    def test_destination_map_survives_backup_restore_and_migration(self):
        from app.services import DestinationStore
        with tempfile.TemporaryDirectory() as folder:
            store=DestinationStore(Path(folder)/'dest.db',Path(folder)/'dest.json',ROOT/'config/destinations.example.json')
            item=store.list()[0];item['map_name']='sala';store.save(item,item['id'])
            copy=store.backup();store.restore(copy)
            self.assertEqual(next(d for d in store.list() if d['name']==item['name'])['map_name'],'sala')
            # Reopen uses the migration path and preserves all records.
            reopened=DestinationStore(Path(folder)/'dest.db',Path(folder)/'dest.json',ROOT/'config/destinations.example.json')
            self.assertEqual(reopened.list(),store.list())

    def test_platform_retirement_preserves_user_data_and_original_driver(self):
        tool=module('retire_platform_files')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'project';backup=Path(folder)/'backup'
            for name in ('software/robot_runtime/base_node.py','software/raspberry/onigiri_udp_tank.py','data/platform.json','data/maps/sala/map.yaml'):
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('preserve')
            tool.retire(root,backup)
            self.assertFalse((root/'software/robot_runtime').exists())
            self.assertTrue((backup/'retired-platforms/software/robot_runtime/base_node.py').is_file())
            self.assertTrue((root/'software/raspberry/onigiri_udp_tank.py').is_file())
            self.assertTrue((root/'data/platform.json').is_file());self.assertTrue((root/'data/maps/sala/map.yaml').is_file())
