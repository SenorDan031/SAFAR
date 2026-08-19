"""Unit tests for the camera abstraction without a real phone or OpenCV."""

from safar.perception.camera import CameraStreamError, PhoneCamera


class FakeFrame:
    shape = (480, 640, 3)


class FakeCapture:
    def __init__(self, opened=True, frame=None):
        self.opened = opened
        self.frame = frame
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        return (self.frame is not None, self.frame)

    def release(self):
        self.released = True
        self.opened = False


def test_phone_camera_reads_and_releases_frame_source():
    capture = FakeCapture(frame=FakeFrame())
    camera = PhoneCamera("http://192.168.1.25:8080/video", lambda _: capture)
    camera.connect()
    assert camera.is_opened()
    assert camera.read().shape == (480, 640, 3)
    camera.release()
    assert capture.released


def test_phone_camera_accepts_rtsp_url():
    camera = PhoneCamera("rtsp://192.168.1.10:8556/live", lambda _: FakeCapture(frame=FakeFrame()))
    camera.connect()
    assert camera.is_opened()


def test_phone_camera_rejects_invalid_or_unavailable_streams():
    invalid = PhoneCamera("not-a-url", lambda _: FakeCapture())
    try:
        invalid.connect()
        assert False, "Expected invalid URL to fail"
    except CameraStreamError:
        pass


def test_phone_camera_reports_missing_or_malformed_frames():
    camera = PhoneCamera("http://192.168.1.25:8080/video", lambda _: FakeCapture(frame=None))
    camera.connect()
    try:
        camera.read()
        assert False, "Expected missing frame to fail"
    except CameraStreamError:
        pass
    unavailable = PhoneCamera("http://192.168.1.25:8080/video", lambda _: FakeCapture(opened=False))
    try:
        unavailable.connect()
        assert False, "Expected unavailable stream to fail"
    except CameraStreamError:
        pass
