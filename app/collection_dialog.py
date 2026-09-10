from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QLabel, QComboBox


class DragCheckList(QListWidget):
    def __init__(self):
        super().__init__()
        self.group_size = 1
        self.drag_state = None
        self.last_row = None

    def apply_group(self, row, state):
        start = row // self.group_size * self.group_size
        for index in range(start, min(start + self.group_size, self.count())):
            item = self.item(index)
            if not item.isHidden():
                item.setCheckState(state)

    def mousePressEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if event.button() == Qt.LeftButton and item:
            self.drag_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
            self.last_row = self.row(item)
            self.apply_group(self.last_row, self.drag_state)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_state is not None:
            point = event.position().toPoint()
            bar = self.verticalScrollBar()
            if point.y() < 20:
                bar.setValue(bar.value() - 1)
            elif point.y() > self.viewport().height() - 20:
                bar.setValue(bar.value() + 1)
            item = self.itemAt(point)
            if item:
                row = self.row(item)
                for index in range(min(row, self.last_row), max(row, self.last_row) + 1):
                    self.apply_group(index, self.drag_state)
                self.last_row = row
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drag_state is not None:
            self.drag_state = None
            self.last_row = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class CollectionDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setWindowTitle('选择要下载的视频')
        self.resize(720, 540)
        self.setMinimumSize(480, 360)
        self.items = items
        layout = QVBoxLayout(self)
        search = QLineEdit()
        search.setPlaceholderText('搜索标题或集数')
        layout.addWidget(search)
        grouping = QComboBox()
        grouping.addItems(['逐集选择', '每5集成组选择', '每10集成组选择'])
        grouping.setToolTip('按列表顺序分组；支持按住鼠标滑动勾选，不合并视频文件。搜索时只操作可见项。')
        layout.addWidget(grouping)
        self.list = DragCheckList()
        grouping.currentIndexChanged.connect(lambda index: setattr(self.list, 'group_size', (1, 5, 10)[index]))
        for index, item in enumerate(items):
            row = QListWidgetItem(item.title)
            row.setData(Qt.UserRole, index)
            row.setFlags(row.flags() | Qt.ItemIsUserCheckable)
            row.setCheckState(Qt.Unchecked)
            row.setToolTip(item.url)
            self.list.addItem(row)
        layout.addWidget(self.list)
        self.count = QLabel()
        layout.addWidget(self.count)
        buttons = QHBoxLayout()
        for text, callback in [('全选可见项', lambda: self.check_visible(True)), ('取消全选', lambda: self.check_visible(False)), ('取消', self.reject), ('加入下载队列', self.accept)]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        search.textChanged.connect(self.filter)
        self.list.itemChanged.connect(self.update_count)
        self.update_count()

    def filter(self, text):
        for index in range(self.list.count()):
            item = self.list.item(index)
            item.setHidden(text.casefold() not in item.text().casefold())

    def check_visible(self, checked):
        for index in range(self.list.count()):
            item = self.list.item(index)
            if not checked or not item.isHidden():
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def selected(self):
        return [self.items[i] for i in range(self.list.count()) if self.list.item(i).checkState() == Qt.Checked]

    def update_count(self, *_):
        self.count.setText(f'共 {len(self.items)} 项，已选 {len(self.selected())} 项；确认后仅加入队列，不自动下载。')
