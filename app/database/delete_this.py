# Personal Finance Dashboard using PyQt5
# Author: ChatGPT
# Date: September 18, 2024

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QGridLayout, QComboBox,
    QLineEdit, QGroupBox, QFormLayout, QStackedWidget, QMessageBox
)
from PyQt5.QtGui import QPixmap, QIcon, QFont, QPainter, QColor
from PyQt5.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import random

# Mock data for the dashboard
categories = ['Housing', 'Transportation', 'Food', 'Utilities', 'Entertainment', 'Healthcare', 'Others']
monthly_expenses = [1200, 300, 400, 150, 200, 100, 50]
monthly_income = 4000
savings = 5000
investments = 10000

# Main application class
class FinanceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personal Finance Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        self.init_ui()

    def init_ui(self):
        self.create_dashboard()
        self.create_details_screen()
        self.central_widget.setCurrentWidget(self.dashboard_screen)

    def create_dashboard(self):
        self.dashboard_screen = QWidget()
        layout = QVBoxLayout()

        # Title
        title = QLabel("Personal Finance Overview")
        title.setFont(QFont('Arial', 24))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Summary Section
        summary_layout = QHBoxLayout()

        # Income Summary
        income_group = QGroupBox("Income")
        income_layout = QVBoxLayout()
        income_label = QLabel(f"${monthly_income}")
        income_label.setFont(QFont('Arial', 20))
        income_label.setAlignment(Qt.AlignCenter)
        income_layout.addWidget(income_label)
        income_group.setLayout(income_layout)
        income_group.setStyleSheet("background-color: #d4edda; border: 1px solid #c3e6cb;")
        summary_layout.addWidget(income_group)

        # Expenses Summary
        expenses_group = QGroupBox("Expenses")
        expenses_layout = QVBoxLayout()
        total_expenses = sum(monthly_expenses)
        expenses_label = QLabel(f"${total_expenses}")
        expenses_label.setFont(QFont('Arial', 20))
        expenses_label.setAlignment(Qt.AlignCenter)
        expenses_layout.addWidget(expenses_label)
        expenses_group.setLayout(expenses_layout)
        expenses_group.setStyleSheet("background-color: #f8d7da; border: 1px solid #f5c6cb;")
        summary_layout.addWidget(expenses_group)

        # Savings Summary
        savings_group = QGroupBox("Savings")
        savings_layout = QVBoxLayout()
        savings_label = QLabel(f"${savings}")
        savings_label.setFont(QFont('Arial', 20))
        savings_label.setAlignment(Qt.AlignCenter)
        savings_layout.addWidget(savings_label)
        savings_group.setLayout(savings_layout)
        savings_group.setStyleSheet("background-color: #fff3cd; border: 1px solid #ffeeba;")
        summary_layout.addWidget(savings_group)

        # Investments Summary
        investments_group = QGroupBox("Investments")
        investments_layout = QVBoxLayout()
        investments_label = QLabel(f"${investments}")
        investments_label.setFont(QFont('Arial', 20))
        investments_label.setAlignment(Qt.AlignCenter)
        investments_layout.addWidget(investments_label)
        investments_group.setLayout(investments_layout)
        investments_group.setStyleSheet("background-color: #d1ecf1; border: 1px solid #bee5eb;")
        summary_layout.addWidget(investments_group)

        layout.addLayout(summary_layout)

        # Charts Section
        charts_layout = QHBoxLayout()

        # Expenses Pie Chart
        expenses_pie_chart = self.create_pie_chart(categories, monthly_expenses, "Monthly Expenses Breakdown")
        charts_layout.addWidget(expenses_pie_chart)

        # Income vs Expenses Bar Chart
        income_expenses_bar_chart = self.create_bar_chart(['Income', 'Expenses'], [monthly_income, total_expenses], "Income vs Expenses")
        charts_layout.addWidget(income_expenses_bar_chart)

        layout.addLayout(charts_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        details_btn = QPushButton("View Details")
        details_btn.clicked.connect(self.show_details)
        btn_layout.addWidget(details_btn)

        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.clicked.connect(self.refresh_data)
        btn_layout.addWidget(refresh_btn)

        layout.addLayout(btn_layout)

        self.dashboard_screen.setLayout(layout)
        self.central_widget.addWidget(self.dashboard_screen)

    def create_pie_chart(self, labels, sizes, title):
        fig, ax = plt.subplots(figsize=(5, 5))
        fig.patch.set_facecolor('#f0f0f0')
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
        ax.axis('equal')
        ax.set_title(title)

        canvas = FigureCanvas(fig)
        return canvas

    def create_bar_chart(self, labels, values, title):
        fig, ax = plt.subplots(figsize=(5, 5))
        fig.patch.set_facecolor('#f0f0f0')
        bars = ax.bar(labels, values, color=['#28a745', '#dc3545'])
        ax.set_title(title)
        ax.set_ylabel('Amount ($)')
        ax.set_ylim(0, max(values) * 1.2)

        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + 0.3, yval + (max(values) * 0.05), f'${yval}', fontsize=12)

        canvas = FigureCanvas(fig)
        return canvas

    def create_details_screen(self):
        self.details_screen = QWidget()
        layout = QVBoxLayout()

        # Title
        title = QLabel("Detailed Financial Information")
        title.setFont(QFont('Arial', 24))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Income Section
        income_group = QGroupBox("Income Details")
        income_layout = QFormLayout()
        self.salary_input = QLineEdit(str(monthly_income))
        self.other_income_input = QLineEdit("0")
        income_layout.addRow("Salary:", self.salary_input)
        income_layout.addRow("Other Income:", self.other_income_input)
        income_group.setLayout(income_layout)
        layout.addWidget(income_group)

        # Expenses Section
        expenses_group = QGroupBox("Expenses Details")
        expenses_layout = QGridLayout()

        self.expense_inputs = []
        for i, category in enumerate(categories):
            label = QLabel(category + ":")
            input_field = QLineEdit(str(monthly_expenses[i]))
            self.expense_inputs.append(input_field)
            expenses_layout.addWidget(label, i // 2, (i % 2) * 2)
            expenses_layout.addWidget(input_field, i // 2, (i % 2) * 2 + 1)

        expenses_group.setLayout(expenses_layout)
        layout.addWidget(expenses_group)

        # Savings and Investments
        savings_investments_layout = QHBoxLayout()

        savings_group = QGroupBox("Savings")
        savings_layout = QVBoxLayout()
        self.savings_input = QLineEdit(str(savings))
        savings_layout.addWidget(self.savings_input)
        savings_group.setLayout(savings_layout)
        savings_investments_layout.addWidget(savings_group)

        investments_group = QGroupBox("Investments")
        investments_layout = QVBoxLayout()
        self.investments_input = QLineEdit(str(investments))
        investments_layout.addWidget(self.investments_input)
        investments_group.setLayout(investments_layout)
        savings_investments_layout.addWidget(investments_group)

        layout.addLayout(savings_investments_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        back_btn = QPushButton("Back to Dashboard")
        back_btn.clicked.connect(self.show_dashboard)
        btn_layout.addWidget(back_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.save_changes)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

        self.details_screen.setLayout(layout)
        self.central_widget.addWidget(self.details_screen)

    def show_details(self):
        self.central_widget.setCurrentWidget(self.details_screen)

    def show_dashboard(self):
        self.central_widget.setCurrentWidget(self.dashboard_screen)
        self.refresh_data()

    def save_changes(self):
        global monthly_income, monthly_expenses, savings, investments

        # Update income
        try:
            monthly_income = float(self.salary_input.text()) + float(self.other_income_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for income.")
            return

        # Update expenses
        new_expenses = []
        for input_field in self.expense_inputs:
            try:
                expense = float(input_field.text())
                new_expenses.append(expense)
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for expenses.")
                return
        monthly_expenses[:] = new_expenses

        # Update savings and investments
        try:
            savings = float(self.savings_input.text())
            investments = float(self.investments_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for savings and investments.")
            return

        QMessageBox.information(self, "Data Saved", "Your changes have been saved.")
        self.show_dashboard()

    def refresh_data(self):
        self.central_widget.removeWidget(self.dashboard_screen)
        self.dashboard_screen.deleteLater()
        self.create_dashboard()
        self.central_widget.setCurrentWidget(self.dashboard_screen)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Exit Application',
                                     "Are you sure you want to exit?", QMessageBox.Yes |
                                     QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

# Entry point of the application
if __name__ == '__main__':
    app = QApplication(sys.argv)
    finance_app = FinanceApp()
    finance_app.show()
    sys.exit(app.exec_())
