from collections import defaultdict
from datetime import datetime
import json
from dotenv import load_dotenv
import os
import subprocess as sp
from utils import time_str_to_minutes
import requests

load_dotenv()


class DataExtractionPipeline:
    def __init__(
        self,
        sonarqube_url: str = os.getenv("SONARQUBE_SERVER_URL"),
        sonarqube_token: str = "",
        repo_name: str = "",
        repo_path: str = "",
    ):
        # Parameters for the Data Extraction Pipeline
        self.sonarqube_url = sonarqube_url
        self.sonarqube_token = sonarqube_token
        self.repo_name = repo_name
        self.repo_path = repo_path

        # Constants for the Data Extraction Pipeline
        self.__clean_code_attribute_categories = [
            "RESPONSIBLE",
            "ADAPTABLE",
            "CONSISTENT",
            "INTENTIONAL",
        ]

        self.__severities = ["LOW", "MEDIUM", "HIGH"]

        self.__quality_attributes = [
            "RELIABILITY",
            "SECURITY",
            "MAINTAINABILITY",
        ]

        self.__code_metrics = [
            # Complexity
            "complexity",
            "cognitive_complexity",
            # Duplication
            "duplicated_blocks",
            "duplicated_files",
            "duplicated_lines",
            "duplicated_lines_density",
            # Issues
            "violations",
            "blocker_violations",
            "critical_violations",
            "major_violations",
            "minor_violations",
            "false_positive_issues",
            # Maintainability
            "code_smells",
            "sqale_index",
            "sqale_rating",
            "sqale_debt_ratio",
            # Reliability
            "bugs",
            "reliability_rating",
            "reliability_remediation_effort",
            # Security
            "vulnerabilities",
            "security_rating",
            "security_remediation_effort",
            "security_hotspots",
            "security_review_rating",
            # Size
            "ncloc",
            "statements",
        ]

        self.__indexing_fields = ["version", "release_date", "timestamp"]

        self.__code_metrics_query_string = ",".join(self.__code_metrics)

        self.__metrics_dict = defaultdict(list)
        self.__clean_code_attribute_dict = defaultdict()

        for metric in self.__indexing_fields + self.__code_metrics:
            self.__metrics_dict[metric] = []

        for category in self.__clean_code_attribute_categories:
            self.__clean_code_attribute_dict[category] = defaultdict(list)

    def __get_tag_list(self, max_output: int | None = 20) -> list[str]:

        repo_path = self.repo_path

        # Subprocess to get the git directory
        sp.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Subprocess to get the git tags in the repo
        result = sp.run(
            ["git", "tag", "-l"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        tag_list = result.stdout.decode("utf-8").split("\n")
        tag_list = [tag for tag in tag_list if tag != ""]

        if max_output is not None and len(tag_list) > max_output:
            tag_list = tag_list[-max_output:]

        return tag_list

    def __get_tag_and_timestamp(
        self, max_output: int | None = 20
    ) -> list[tuple[str, str, int]]:
        """
        This function returns a list of tuples containing the tag, release date and timestamp of the tag from the
        prespecified repository.

        Returns:
        list[tuple[str, str, int]]: A list of tuples containing the tag, release date and timestamp of the tag from the
        prespecified repository.

        """
        repo_path = self.repo_path
        tag_list = self.__get_tag_list(max_output=max_output)
        tag_and_timestamp = []

        for tag in tag_list:
            result = sp.run(
                ["git", "log", "-1", "--format=%cd %ct", "--date=short", tag],
                cwd=repo_path,
                capture_output=True,
                check=True,
                text=True,
            )

            date, timestamp = result.stdout.strip().split()
            tag_and_timestamp.append((tag, date, int(timestamp)))
            # print(result.stdout.strip())
        return tag_and_timestamp

    def __get_version_tags_by_year(
        self, data: list[tuple[str, str, int]], max_per_year: int | None = 5
    ):
        """
        This function takes a list of tuples containing version, release date and timestamp
        and returns a list of tuples containing version, release date and timestamp
        for the most recent versions of each year.

        Parameters:
        data (list[tuple[str, str, int]]): A list of tuples containing version, release date and timestamp
        max_per_year (int): The maximum number of versions to be selected per year. If None, all versions are selected.

        Returns:
        list[tuple[str, str, int]]: A list of tuples containing version, release date and timestamp
        """
        versions_by_year = defaultdict(list)

        datetime_converted_data = [
            (version, datetime.strptime(date, "%Y-%m-%d"), timestamp)
            for version, date, timestamp in data
        ]

        for version, release_date, timestamp in datetime_converted_data:
            year = release_date.year
            versions_by_year[year].append((version, release_date, timestamp))

        selected_versions = []

        for year in sorted(versions_by_year.keys()):

            versions_of_this_year = versions_by_year[year]

            if max_per_year is None:
                selected_versions.extend(versions_of_this_year)
            else:
                selected_versions.extend(
                    versions_of_this_year[
                        : min(max_per_year, len(versions_of_this_year))
                    ]
                )

        return [
            (version, release_date.strftime("%Y-%m-%d"), timestamp)
            for version, release_date, timestamp in selected_versions
        ]

    def __checkout_to_tag(self, tag: str):
        repo_path = self.repo_path
        result = sp.run(
            ["git", "checkout", tag],
            cwd=repo_path,
            capture_output=True,
            check=True,
            text=True,
        )
        print("Checkedout to tag:", tag)

    def __sonar_scan(self, tag: str):
        """
        This function runs a SonarQube scan for the specified tag.
        """
        print("Running SonarQube scan for tag:", tag)
        result = sp.run(
            [
                "sonar-scanner",
                "-D",
                f"sonar.projectBaseDir={self.repo_path}",
                "-D",
                "sonar.projectVersion=" + tag,
                "-D",
                f"sonar.projectKey={self.repo_name}",
                "-D",
                "sonar.sources=.",
                "-D",
                f"sonar.host.url={self.sonarqube_url}",
                "-D",
                "sonar.login=" + self.sonarqube_token,
            ],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
            text=True,
            shell=True,
        )
        print("SonarQube scan completed for tag:", tag)

    def __get_metrics(self) -> dict:
        """
        This function returns the metrics for the specified repository.

        Returns:
        dict: A dictionary containing the metrics for the specified repository.
        """

        print("Getting metrics from SonarQube")

        url = f"{self.sonarqube_url}/api/measures/component"
        params = {
            "component": self.repo_name,
            "metricKeys": self.__code_metrics_query_string,
        }

        response = requests.get(url, params=params)
        print("Metrics API response: ", response)
        result = response.json()
        print("Metrics received from SonarQube")

        return result

    def __get_metrics_from_version_tags(self, tag: str, date: str, timestamp: int):

        metrics_result = self.__get_metrics()

        self.__metrics_dict["version"].append(tag)
        self.__metrics_dict["release_date"].append(date)
        self.__metrics_dict["timestamp"].append(timestamp)

        for metric in metrics_result["component"]["measures"]:
            self.__metrics_dict[metric["metric"]].append(metric["value"])

        return self.__metrics_dict

    def __get_quality_issue_values_from_api(
        self, clean_code_category: str, severity: str
    ) -> tuple[int, int, int, int]:
        """
        Returns:
        A tuple of (total_security_issues, total_reliability_issues, total_maintainability_issues, total_debt)
        """

        url = f"{self.sonarqube_url}/api/issues/search"
        params = {"cleanCodeAttributeCategories": clean_code_category}

        response = requests.get(url, params=params)
        print("Quality Issues API response: ", response)

        result = response.json()

        issues_list = result["issues"]

        # Get the software quality, maintainability and debt from the issues list
        filtered_issues_list = [
            {
                "software_quality_category": issue["impacts"][0]["softwareQuality"],
                "severity": issue["impacts"][0]["severity"],
                "debt": time_str_to_minutes(issue["debt"]),
            }
            for issue in issues_list
            if issue["type"] == "CODE_SMELL"
            and issue["impacts"][0]["severity"] == severity
        ]

        # Get the total number of security, reliability and maintainability quality issue count and debt
        total_security_issues = len(
            [
                issue
                for issue in filtered_issues_list
                if issue["software_quality_category"] == "SECURITY"
            ]
        )
        total_reliability_issues = len(
            [
                issue
                for issue in filtered_issues_list
                if issue["software_quality_category"] == "RELIABILITY"
            ]
        )
        total_maintainability_issues = len(
            [
                issue
                for issue in filtered_issues_list
                if issue["software_quality_category"] == "MAINTAINABILITY"
            ]
        )

        total_debt = sum([issue["debt"] for issue in filtered_issues_list])

        return (
            total_security_issues,
            total_reliability_issues,
            total_maintainability_issues,
            total_debt,
        )

    # def extract_metrics_data(self)

    def __extract_clean_code_data(self, tag: str, date: str, timestamp: int):
        for clean_code_category in self.__clean_code_attribute_categories:
            self.__clean_code_attribute_dict[clean_code_category]["version"].append(tag)
            self.__clean_code_attribute_dict[clean_code_category]["date"].append(date)
            self.__clean_code_attribute_dict[clean_code_category]["timestamp"].append(
                timestamp
            )

            for severity in self.__severities:
                (
                    total_security_issues,
                    total_reliability_issues,
                    total_maintainability_issues,
                    total_debt,
                ) = self.__get_quality_issue_values_from_api(
                    clean_code_category, severity
                )

                self.__clean_code_attribute_dict[clean_code_category][
                    f"security_issues_{severity.lower()}"
                ].append(total_security_issues)

                self.__clean_code_attribute_dict[clean_code_category][
                    f"reliability_issues_{severity.lower()}"
                ].append(total_reliability_issues)

                self.__clean_code_attribute_dict[clean_code_category][
                    f"maintainability_issues_{severity.lower()}"
                ].append(total_maintainability_issues)

                self.__clean_code_attribute_dict[clean_code_category][
                    f"total_debt_{severity.lower()}"
                ].append(total_debt)

    def get_metrics_data(
        self, max_tags: int | None = 20, max_tags_per_year: int | None = 5
    ):
        tag_and_timestamp = self.__get_tag_and_timestamp(max_output=max_tags)
        version_tags = self.__get_version_tags_by_year(
            tag_and_timestamp, max_per_year=max_tags_per_year
        )

        for tag, date, timestamp in version_tags:
            self.__checkout_to_tag(tag)
            self.__sonar_scan(tag)
            self.__get_metrics_from_version_tags(tag, date, timestamp)
            self.__extract_clean_code_data(tag, date, timestamp)

        return self.__metrics_dict, self.__clean_code_attribute_dict
