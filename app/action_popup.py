"""Shared rounded action/selection popup with one surface and keyboard navigation."""
from PySide6.QtCore import Qt, QPoint, Signal, QSize
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QGraphicsDropShadowEffect)


class ActionPopup(QWidget):
    def __init__(self, entries, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setObjectName('ActionPopup')
        self.setStyleSheet('''
            QFrame#ActionPopupCard { background: white; border: none; border-radius: 11px; }
            QPushButton#PopupAction { background: transparent; color: #40494d; border: none;
                outline: none; border-radius: 6px; min-height: 34px; max-height: 34px;
                padding: 0 10px; text-align: left; font-size: 14px; font-weight: 400; }
            QPushButton#PopupAction:hover, QPushButton#PopupAction:focus { background: #eeeeee; }
            QPushButton#PopupAction:disabled { color: #92999d; }
            QFrame#PopupDivider { background: #e1e5e7; border: none; }
        ''')
        outer = QVBoxLayout(self); outer.setContentsMargins(16,16,16,16)
        card = QFrame(); card.setObjectName('ActionPopupCard'); outer.addWidget(card)
        shadow = QGraphicsDropShadowEffect(card); shadow.setBlurRadius(22)
        shadow.setOffset(0,2); shadow.setColor(QColor(0,0,0,32)); card.setGraphicsEffect(shadow)
        layout = QVBoxLayout(card); layout.setContentsMargins(6,6,6,6); layout.setSpacing(2)
        self.buttons = []
        selection_menu = all(entry is None or entry[1].isNull() for entry in entries)
        for entry in entries:
            if entry is None:
                line = QFrame(); line.setObjectName('PopupDivider'); line.setFixedHeight(1)
                layout.addSpacing(2); layout.addWidget(line); layout.addSpacing(2); continue
            text, icon, callback, checked, enabled = entry
            button = QPushButton(); button.setObjectName('PopupAction')
            button.setEnabled(enabled); button.setAccessibleName(text)
            row=QHBoxLayout(button);row.setContentsMargins(8,0,8,0);row.setSpacing(10)
            if selection_menu:
                tick=QLabel('✓' if checked else '')
                tick.setFixedWidth(20)
                accent = parent.property('popupAccent') if parent else None
                tick.setStyleSheet(f'color:{accent or "#278575"};background:transparent;')
                tick.setAttribute(Qt.WA_TransparentForMouseEvents)
                row.addWidget(tick)
            if not icon.isNull():
                image=QLabel();image.setObjectName('PopupActionIcon');image.setFixedSize(20,20)
                image.setPixmap(icon.pixmap(QSize(20,20), self.devicePixelRatioF()))
                image.setAttribute(Qt.WA_TransparentForMouseEvents)
                row.addWidget(image)
            label=QLabel(text);label.setStyleSheet('color:#344650;background:transparent;font-size:14px;')
            label.setAttribute(Qt.WA_TransparentForMouseEvents)
            row.addWidget(label,1)
            button.setProperty('actionText',text)
            button.clicked.connect(lambda _=False, cb=callback: self._choose(cb))
            layout.addWidget(button); self.buttons.append(button)
        self.setMinimumWidth(max(222, max((b.fontMetrics().horizontalAdvance(b.property('actionText'))+100 for b in self.buttons), default=222)))

    def _choose(self, callback):
        self.close()
        callback()

    def open_for(self, anchor):
        self.adjustSize()
        rect = anchor.screen().availableGeometry()
        # The visible card, not its transparent shadow margin, aligns with the anchor.
        point = anchor.mapToGlobal(QPoint(0, anchor.height()+8)) - QPoint(16,16)
        if point.y()+self.height()>rect.bottom():
            point.setY(anchor.mapToGlobal(QPoint(0,0)).y()-self.height()-8+16)
        point.setX(max(rect.left(),min(point.x(),rect.right()-self.width()+1)))
        point.setY(max(rect.top(),min(point.y(),rect.bottom()-self.height()+1)))
        self.move(point); self.show()
        for button in self.buttons:
            if button.isEnabled(): button.setFocus(Qt.PopupFocusReason); break

    def keyPressEvent(self, event):
        enabled=[b for b in self.buttons if b.isEnabled()]
        if event.key()==Qt.Key_Escape: self.close(); return
        if event.key() in (Qt.Key_Up,Qt.Key_Down,Qt.Key_Home,Qt.Key_End) and enabled:
            index=next((i for i,b in enumerate(enabled) if b.hasFocus()),0)
            if event.key()==Qt.Key_Home: index=0
            elif event.key()==Qt.Key_End: index=len(enabled)-1
            else: index=(index+(1 if event.key()==Qt.Key_Down else -1))%len(enabled)
            enabled[index].setFocus(Qt.TabFocusReason); return
        if event.key() in (Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space):
            for button in enabled:
                if button.hasFocus(): button.click(); return
        super().keyPressEvent(event)


class MenuFilterButton(QPushButton):
    currentIndexChanged = Signal(int)

    def __init__(self, arrow: QIcon, parent=None):
        super().__init__(parent)
        self.items=[]; self.index=-1; self.popup=None
        self.setObjectName('HistoryFilter')
        self.setMinimumHeight(36)
        layout=QHBoxLayout(self); layout.setContentsMargins(12,0,10,0); layout.setSpacing(12)
        self.label=QLabel(); self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        glyph=QLabel(); glyph.setPixmap(arrow.pixmap(12,12)); glyph.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self.label); layout.addWidget(glyph)
        self.clicked.connect(self._open)

    def addItem(self,text,data=None):
        self.items.append((text,data))
        if self.index<0: self.setCurrentIndex(0)

    def clear(self): self.items.clear(); self.index=-1; self.label.clear()
    def currentIndex(self): return self.index
    def currentData(self): return self.items[self.index][1] if self.index>=0 else None
    def currentText(self): return self.items[self.index][0] if self.index>=0 else ''
    def findData(self,data): return next((i for i,(_,value) in enumerate(self.items) if value==data),-1)

    def setCurrentIndex(self,index):
        if not 0<=index<len(self.items): return
        changed=self.index!=index; self.index=index
        self.label.setText(self.items[index][0]); self.setAccessibleName(self.items[index][0])
        if changed: self.currentIndexChanged.emit(index)

    def _open(self):
        if self.popup and self.popup.isVisible(): self.popup.close(); return
        entries=[(text,QIcon(),lambda i=i:self.setCurrentIndex(i),i==self.index,True)
                 for i,(text,_) in enumerate(self.items)]
        self.popup=ActionPopup(entries,self)
        popup=self.popup
        popup.destroyed.connect(lambda:self._popup_destroyed(popup))
        self.popup.open_for(self)

    def _popup_destroyed(self,popup):
        if self.popup is popup:self.popup=None
