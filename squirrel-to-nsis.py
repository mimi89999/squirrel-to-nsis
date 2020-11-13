from typing import Dict, IO, List

import argparse
import shutil
import subprocess
import tempfile
import zipfile

from pathlib import Path, PureWindowsPath
from xml.etree import ElementTree


UNINST_ROOT: str = 'Software/Microsoft/Windows/CurrentVersion/Uninstall'


class Nuspec:
    def __init__(self, file: IO):
        ns: Dict[str, str] = {
            'nuspec': 'http://schemas.microsoft.com/packaging/2011/08/nuspec.xsd'
        }
        metadata = ElementTree.fromstring(file.read()).find('nuspec:metadata', ns)
        self.iden: str = metadata.find('nuspec:id', ns).text
        self.version: str = metadata.find('nuspec:version', ns).text
        self.title: str = metadata.find('nuspec:title', ns).text
        self.authors: str = metadata.find('nuspec:authors', ns).text
        self.description: str = metadata.find('nuspec:description', ns).text


def write_nsi(nuspec: Nuspec, folder: str, subdir: str):
    with open(Path(folder, 'setup.nsi'), 'w') as nsi_file:
        uninst_key: str = PureWindowsPath(UNINST_ROOT, nuspec.iden)
        print(uninst_key)
        nsi_file.write('Unicode True\n')
        nsi_file.write('Name "{}"\n'.format(nuspec.title))
        nsi_file.write('Outfile "setup.exe"\n')
        nsi_file.write('InstallDir "$PROGRAMFILES\\{}"\n'.format(nuspec.iden))
        nsi_file.write('Section\n')
        nsi_file.write('SetOutPath "$INSTDIR"\n')
        nsi_file.write('File /r {}\n'.format(subdir))
        nsi_file.write('CreateShortcut "$SMPROGRAMS\\{iden}.lnk" \
                 "$INSTDIR\\{iden}\\{iden}.exe"\n'
                 .format(iden=nuspec.iden))
        nsi_file.write('WriteUninstaller "$INSTDIR\\uninstall.exe"\n')
        nsi_file.write('WriteRegStr HKLM "{}" "DisplayName" "{}"\n'
                 .format(uninst_key, nuspec.title))
        nsi_file.write('WriteRegStr HKLM "{}" \
                 "UninstallString" "$\\"$INSTDIR\\uninstall.exe$\\""\n'
                 .format(uninst_key))
        nsi_file.write('WriteRegStr HKLM "{}" \
                 "QuietUninstallString" "$\\"$INSTDIR\\uninstall.exe$\\" /S"\n'
                 .format(uninst_key))
        nsi_file.write('SectionEnd\n')
        nsi_file.write('Section "Uninstall"\n')
        nsi_file.write('Delete "$INSTDIR\\uninstall.exe"\n')
        nsi_file.write('Delete "$SMPROGRAMS\\{}.lnk"\n'.format(nuspec.iden))
        nsi_file.write('RMDir /r "$INSTDIR"\n')
        nsi_file.write('DeleteRegKey HKLM "{}"\n'
                 .format(uninst_key))
        nsi_file.write('SectionEnd\n')

def main(squirrel: str, nsis: str):
    nuspec: Nuspec
    with tempfile.TemporaryDirectory() as tempdir:
        with zipfile.ZipFile(squirrel) as container:
            name: str
            package: str
            with container.open('RELEASES') as releases:
                package = releases.read().split()[1].decode()
                name = package.rsplit('-', maxsplit=2)[0]
            with zipfile.ZipFile(container.open(package)) as nupkg:
                with nupkg.open(name + '.nuspec') as nuspecfile:
                    nuspec = Nuspec(nuspecfile)
                for file in nupkg.namelist():
                    if file.startswith('lib/net45/') and file.lstrip('lib/net45/') \
                                 not in ['', 'squirrel.exe']:
                        nupkg.extract(file, path=tempdir)

        write_nsi(nuspec=nuspec, folder=tempdir, subdir='lib/net45/')
        subprocess.run(['makensis', Path(tempdir, 'setup.nsi')])
        shutil.move(Path(tempdir, 'setup.exe'), Path(nsis))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('squirrel')
    parser.add_argument('nsis')
    args = parser.parse_args()
    main(args.squirrel, args.nsis)
