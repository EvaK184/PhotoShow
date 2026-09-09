"""Desktop folder browser and Android Storage Access Framework picker."""

import os
import string

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.utils import platform

from sources import FolderSource


class FolderPicker(ModalView):
    def __init__(self, selected, initial=None, **kwargs):
        super().__init__(size_hint=(0.94, 0.9), **kwargs)
        self.selected = selected
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        content.add_widget(Label(text="Choose a source folder", size_hint_y=None,
                                 height=dp(36)))
        navigation = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        home = os.path.expanduser("~")
        self.path_input = TextInput(multiline=False)
        self.path_input.bind(on_text_validate=self.go_to_path)
        navigation.add_widget(self.path_input)
        go = Button(text="Go", size_hint_x=None, width=dp(48))
        go.bind(on_release=self.go_to_path)
        navigation.add_widget(go)
        if platform == "win":
            drives = [f"{letter}:\\" for letter in string.ascii_uppercase
                      if os.path.isdir(f"{letter}:\\")]
            drive = Spinner(text="Drive", values=drives, size_hint_x=None, width=dp(80))
            drive.bind(text=lambda _widget, path: self.navigate(path))
            navigation.add_widget(drive)
        content.add_widget(navigation)
        self.browser = FileChooserListView(
            path=initial if initial and os.path.isdir(initial) else home,
            dirselect=True, filters=[lambda directory, name: os.path.isdir(name)],
        )
        self.path_input.text = self.browser.path
        self.browser.bind(path=self._path_changed)
        content.add_widget(self.browser)
        self.message = Label(text="Open a folder, then choose Use this folder.",
                             size_hint_y=None, height=dp(44), halign="center")
        self.message.bind(size=lambda widget, size: setattr(widget, "text_size", size))
        content.add_widget(self.message)
        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        cancel = Button(text="Cancel")
        cancel.bind(on_release=self.dismiss)
        choose = Button(text="Use this folder")
        choose.bind(on_release=self.choose)
        actions.add_widget(cancel)
        actions.add_widget(choose)
        content.add_widget(actions)
        self.add_widget(content)

    def _path_changed(self, _browser, path):
        self.path_input.text = path
        self.browser.selection = []

    def navigate(self, path):
        path = os.path.abspath(os.path.expanduser(path))
        if os.path.isdir(path):
            self.browser.path = path
            self.browser.selection = []
        else:
            self.message.text = "That folder is unavailable. Choose another folder."

    def go_to_path(self, *_args):
        self.navigate(self.path_input.text)

    def choose(self, *_args):
        path = (self.browser.selection[0] if self.browser.selection
                else self.browser.path)
        if not os.path.isdir(path):
            self.message.text = "Choose an available folder."
            return
        self.selected(FolderSource("local", os.path.abspath(path), os.path.abspath(path)))
        self.dismiss()


class AndroidFolderPicker:
    REQUEST_CODE = 4107

    def __init__(self, selected, failed):
        self.selected = selected
        self.failed = failed
        self.active = False

    def open(self):
        from android import activity
        from android.runnable import run_on_ui_thread
        from jnius import autoclass

        if self.active:
            return
        self.active = True
        activity.bind(on_activity_result=self._result)

        @run_on_ui_thread
        def launch():
            try:
                intent_class = autoclass("android.content.Intent")
                intent = intent_class(intent_class.ACTION_OPEN_DOCUMENT_TREE)
                intent.addFlags(intent_class.FLAG_GRANT_READ_URI_PERMISSION
                                | intent_class.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
                                | intent_class.FLAG_GRANT_PREFIX_URI_PERMISSION)
                intent.putExtra(intent_class.EXTRA_LOCAL_ONLY, True)
                autoclass("org.kivy.android.PythonActivity").mActivity.startActivityForResult(
                    intent, self.REQUEST_CODE)
            except Exception:
                self.close()
                Clock.schedule_once(lambda _dt: self.failed(
                    "The system folder picker could not be opened."), 0)
        launch()

    def close(self):
        if self.active:
            from android import activity
            activity.unbind(on_activity_result=self._result)
            self.active = False

    def _result(self, request_code, result_code, intent):
        if request_code != self.REQUEST_CODE:
            return
        self.close()
        if result_code != -1 or intent is None:
            return
        try:
            from jnius import autoclass
            uri = intent.getData()
            resolver = autoclass("org.kivy.android.PythonActivity").mActivity.getContentResolver()
            resolver.takePersistableUriPermission(uri, 1)  # Read access only.
            contract = autoclass("android.provider.DocumentsContract")
            label = str(contract.getTreeDocumentId(uri))
            source = FolderSource("android_tree", str(uri.toString()), label)
            Clock.schedule_once(lambda _dt: self.selected(source), 0)
        except Exception:
            Clock.schedule_once(lambda _dt: self.failed(
                "Folder access was not granted. Please choose the folder again."), 0)
