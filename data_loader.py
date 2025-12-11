#  "THE BEER-WARE LICENSE" (Revision 42):
#
#  <y.sukhorukov.uav@gmail.com> wrote this file.
#  As long as you retain this notice you can do whatever you want with this stuff.
#  If we meet some day, and you think this stuff is worth it, you can buy me a beer in return.
#  Yuriy Sukhorukov

import asyncio
import pickle
import re
from io import StringIO
from pathlib import Path
from typing import Optional, Iterable
from urllib.parse import urljoin

import numpy as np
from tqdm import tqdm

from models import Prop, Columns


class DataLoader:
    path: Path
    force_download: bool
    batch_size: int

    MAIN_API = "https://www.apcprop.com/"
    PERF_DATA = "technical-information/performance-data/"
    PROP_REGEX = re.compile("PER3_(?P<name>\d+x\d+.*)\.dat")
    PROP_DIMENSION_REGEX = re.compile("(?P<dia>(\d+(\.\d+)?))x(?P<pitch>(\d+(\.\d+)?)).*")

    def __init__(self, path: Optional[Path], force_download: Optional[bool] = False, batch_size: int = 10) -> None:
        self.path = path
        self.force_download = force_download
        self.batch_size = batch_size

    def load(self) -> list[Prop]:
        if self.path.exists() and self.path.is_file() and not self.force_download:
            # pre-cached data exists
            return self._load_from_disk()

        else:
            # No pre-cached data
            return self._fetch_from_apc()


    def _load_from_disk(self) -> list[Prop]:
        # Pre-cached data existing
        print(f"Found {self.path} with data. Skipping download.")
        with open(self.path, 'rb') as f:
            return pickle.load(f)


    def _fetch_from_apc(self) -> list[Prop]:
        from stealth_requests import StealthSession, AsyncStealthSession
        print(f"Downloading data from APC to {self.path}...")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        sr = StealthSession()
        body = sr.get(urljoin(self.MAIN_API, self.PERF_DATA))

        # Get the list of all props with links and names
        props = [
            Prop(
                name=self.PROP_REGEX.search(str(element.xpath("text()"))).group('name').lower(),
                link=urljoin(self.MAIN_API, str(element.xpath("@href")[0]))
            )
            for element in body.xpath('//*[@class="listcols"]/a')
        ]

        async def fetch_prop_info(prop: Prop, session: AsyncStealthSession):
            prop_data = (await session.get(prop.link)).text
            header, *tables = prop_data.split("PROP RPM")
            rpms = []
            extracted = {}

            for table in tables:
                rpm = int(re.sub('\s|=', '', table.split('\n')[0]))
                rpms.append(rpm)
                array_data = np.genfromtxt(
                    StringIO(table),
                    skip_header=1,
                    usecols=[x.value for x in Columns],
                    names=True,
                    dtype=None,
                    invalid_raise=False,
                    encoding='utf-8'
                )

                for i, k in zip(array_data.dtype.names, Columns):
                    extracted[k] = extracted.get(k, []) + [array_data[i][1:]]

            matrices = {
                k: np.vstack(list(zip(*v))).T.astype(np.float32)
                for k, v in extracted.items()
            }

            matrices[Columns.AIRSPEED] *= 0.44704  # Convert to the science units
            rpm_array = np.array(rpms)

            prop.matrices = matrices
            prop.rpms = rpm_array

            match = self.PROP_DIMENSION_REGEX.search(header)
            prop.dia = float(match.group('dia'))
            prop.pitch = float(match.group('pitch'))

        # Fetch the whole thing in batches
        async def batched_fetch_data(props_list: list[Prop]):
            session = AsyncStealthSession()
            print("Fetching data from APC...")
            for batch_n in tqdm(range(0, len(props_list), self.batch_size)):
                batch = props_list[batch_n:batch_n + self.batch_size]
                await asyncio.gather(*[fetch_prop_info(p, session) for p in batch])
        asyncio.run(batched_fetch_data(props))

        pickle.dump(props, open(self.path, 'wb'))
        return props