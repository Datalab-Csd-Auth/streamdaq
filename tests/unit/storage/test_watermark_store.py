from streamdaq.storage.watermark_store import WatermarkStore


class TestWatermarkStore:
    def test_absent_watermarks_read_as_none(self, tmp_path):
        store = WatermarkStore(str(tmp_path / "task_a"))
        try:
            assert store.read_instant_watermark() is None
            assert store.read_window_watermark() is None
        finally:
            store.close()

    def test_writes_survive_reopen(self, tmp_path):
        path = str(tmp_path / "task_a")
        writer = WatermarkStore(path)
        writer.advance_instant_to(1500)
        writer.advance_window_to(2000)
        writer.close()

        reader = WatermarkStore(path)
        try:
            assert reader.read_instant_watermark() == 1500
            assert reader.read_window_watermark() == 2000
        finally:
            reader.close()

    def test_advance_only_keeps_the_maximum(self, tmp_path):
        store = WatermarkStore(str(tmp_path / "task_a"))
        try:
            store.advance_window_to(2000)
            store.advance_window_to(1000)
            assert store.read_window_watermark() == 2000
            store.advance_window_to(3000)
            assert store.read_window_watermark() == 3000
        finally:
            store.close()

    def test_instant_and_window_watermarks_are_independent(self, tmp_path):
        store = WatermarkStore(str(tmp_path / "task_a"))
        try:
            store.advance_instant_to(1100)
            assert store.read_window_watermark() is None
            store.advance_window_to(2000)
            assert store.read_instant_watermark() == 1100
            assert store.read_window_watermark() == 2000
        finally:
            store.close()

    def test_per_task_isolation(self, tmp_path):
        store_a = WatermarkStore(str(tmp_path / "task_a"))
        store_b = WatermarkStore(str(tmp_path / "task_b"))
        try:
            store_a.advance_window_to(1000)
            store_b.advance_window_to(2000)
            assert store_a.read_window_watermark() == 1000
            assert store_b.read_window_watermark() == 2000
        finally:
            store_a.close()
            store_b.close()
