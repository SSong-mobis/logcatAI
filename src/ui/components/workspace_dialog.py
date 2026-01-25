from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QListWidget,
                             QListWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt

class WorkspaceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Workspace Manager")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Workspace List
        layout.addWidget(QLabel("Saved Workspaces:"))
        self.workspace_list = QListWidget()
        # Mock saved workspaces
        self.workspace_list.addItem("https://github.com/example/repo1.git (main)")
        self.workspace_list.addItem("https://github.com/example/repo2.git (develop)")
        layout.addWidget(self.workspace_list)
        
        # New Workspace Input
        layout.addWidget(QLabel("Add New Workspace:"))
        
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Git URL:"))
        self.git_url_input = QLineEdit()
        self.git_url_input.setPlaceholderText("https://github.com/example/repo.git")
        url_layout.addWidget(self.git_url_input)
        layout.addLayout(url_layout)
        
        branch_layout = QHBoxLayout()
        branch_layout.addWidget(QLabel("Branch:"))
        self.branch_combo = QComboBox()
        self.branch_combo.setEditable(True)
        self.branch_combo.addItem("main")
        self.branch_combo.addItem("develop")
        branch_layout.addWidget(self.branch_combo)
        
        self.refresh_btn = QPushButton("Refresh Branches")
        branch_layout.addWidget(self.refresh_btn)
        layout.addLayout(branch_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Workspace")
        self.load_btn = QPushButton("Load Selected")
        self.delete_btn = QPushButton("Delete Selected")
        self.cancel_btn = QPushButton("Cancel")
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.load_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.add_btn.clicked.connect(self._add_workspace)
        self.load_btn.clicked.connect(self._load_selected)
        self.delete_btn.clicked.connect(self._delete_selected)
        self.cancel_btn.clicked.connect(self.reject)
        self.workspace_list.itemDoubleClicked.connect(self._load_selected)
    
    def _add_workspace(self):
        url = self.git_url_input.text().strip()
        branch = self.branch_combo.currentText().strip()
        
        if not url:
            QMessageBox.warning(self, "Invalid Input", "Please enter a Git URL.")
            return
        
        item_text = f"{url} ({branch})"
        self.workspace_list.addItem(item_text)
        self.git_url_input.clear()
    
    def _load_selected(self):
        item = self.workspace_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a workspace to load.")
            return
        self.accept()
    
    def _delete_selected(self):
        item = self.workspace_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a workspace to delete.")
            return
        
        reply = QMessageBox.question(self, "Delete Workspace", 
                                    f"Are you sure you want to delete:\n{item.text()}?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.workspace_list.takeItem(self.workspace_list.row(item))
    
    def get_selected_project(self):
        item = self.workspace_list.currentItem()
        if item:
            text = item.text()
            # Extract URL from "url (branch)" format
            if " (" in text:
                return text.split(" (")[0]
            return text
        return None
    
    def get_selected_branch(self):
        item = self.workspace_list.currentItem()
        if item:
            text = item.text()
            # Extract branch from "url (branch)" format
            if " (" in text and text.endswith(")"):
                return text.split(" (")[1].rstrip(")")
            return "main"  # default
        return None
