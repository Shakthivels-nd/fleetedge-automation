#!/bin/bash
# ------------------------------
# Run tests and Generate Allure HTML report
# ------------------------------

RESULTS_DIR="src/reports/allure-results"
REPORT_DIR="src/reports/allure-report"


echo "Running tests with pytest..."
pytest --alluredir="$RESULTS_DIR" -v

if [ $? -eq 0 ]; then
    echo "Tests completed successfully."
else
    echo "Some tests failed. Check pytest output above."
fi


echo "Generating Allure HTML report..."
allure generate "$RESULTS_DIR" -o "$REPORT_DIR" --clean --report-name "App Package Test Report"
if [ $? -ne 0 ]; then
    echo "Failed to generate Allure report. Make sure 'allure' is installed."
    exit 1
fi
