from uuid import UUID


class DownloadJob:
    def __init__(self, *, id: UUID, video_id: UUID) -> None:
        self.id = id
        self.video_id = video_id
