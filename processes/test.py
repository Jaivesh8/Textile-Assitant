import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tabulate import tabulate
import re
import google.generativeai as genai
import json
class ManufacturingLocationAnalyzer:
    def __init__(self, proximity_weight=0.15):
        """
        Initializes the Manufacturing Location Analyzer with industry-specific parameters,
        investment scale parameters, industrial zone preferences, and a weight for
        neighboring the preferred state.

        Args:
            proximity_weight (float): Weightage given to states neighboring the
                                      preferred state (default: 0.15).
        """
        self.proximity_weight = proximity_weight
        self.load_datasets()

        # Define industry-specific parameters
        self.electricity_intensity = {
            "textile": {"intensity": "medium", "electricity_weight": 0.4, "description": "Moderate electricity consumption"},
            "electronics": {"intensity": "high", "electricity_weight": 0.6, "description": "High electricity consumption for precision manufacturing"},
            "food processing": {"intensity": "medium", "electricity_weight": 0.3, "description": "Refrigeration and processing equipment"},
            "automotive": {"intensity": "high", "electricity_weight": 0.5, "description": "Heavy machinery and assembly lines"},
            "pharmaceutical": {"intensity": "medium-high", "electricity_weight": 0.4, "description": "Controlled environments and specialized equipment"},
            "chemical": {"intensity": "very high", "electricity_weight": 0.7, "description": "Energy-intensive processes"},
            "furniture": {"intensity": "low", "electricity_weight": 0.2, "description": "Primarily mechanical operations"},
            "plastics": {"intensity": "high", "electricity_weight": 0.5, "description": "Heating and molding processes"},
            "paper": {"intensity": "very high", "electricity_weight": 0.6, "description": "Pulping and drying processes"},
            "metal": {"intensity": "very high", "electricity_weight": 0.7, "description": "Smelting and forging operations"}
        }

        # Investment scale parameters
        self.investment_scales = {
            "small": {
                "range": "Under ₹1 crore",
                "weights": {
                    "electricity": 0.3,
                    "labor": 0.3,
                    "ease_of_business": 0.2,
                    "infrastructure": 0.2
                }
            },
            "medium": {
                "range": "₹1-10 crore",
                "weights": {
                    "electricity": 0.25,
                    "labor": 0.25,
                    "ease_of_business": 0.25,
                    "infrastructure": 0.25
                }
            },
            "large": {
                "range": "Above ₹10 crore",
                "weights": {
                    "electricity": 0.2,
                    "labor": 0.2,
                    "ease_of_business": 0.3,
                    "infrastructure": 0.3
                }
            }
        }

        # Define industrial zone preferences by industry
        self.industry_zone_preferences = {
            "textile": ["Special Economic Zones (SEZs)", "Industrial Parks & Clusters"],
            "electronics": ["Special Economic Zones (SEZs)", "PLI Scheme Zones"],
            "food processing": ["Industrial Parks & Clusters", "PLI Scheme Zones"],
            "automotive": ["Industrial Corridors", "PLI Scheme Zones"],
            "pharmaceutical": ["Special Economic Zones (SEZs)", "PLI Scheme Zones", "Industrial Parks & Clusters"],
            "chemical": ["National Investment and Manufacturing Zones (NIMZs)", "Industrial Parks & Clusters"],
            "furniture": ["Industrial Parks & Clusters"],
            "plastics": ["Industrial Parks & Clusters", "National Investment and Manufacturing Zones (NIMZs)"],
            "paper": ["Industrial Parks & Clusters"],
            "metal": ["National Investment and Manufacturing Zones (NIMZs)", "Industrial Corridors"]
        }

        # Define a dictionary of neighboring states for proximity weighting
        self.neighboring_states = {
            "Andhra Pradesh": ["Telangana", "Tamil Nadu", "Karnataka", "Odisha", "Chhattisgarh"],
            "Arunachal Pradesh": ["Assam", "Nagaland"],
            "Assam": ["Arunachal Pradesh", "Nagaland", "Manipur", "Meghalaya", "Tripura", "Mizoram", "West Bengal"],
            "Bihar": ["Uttar Pradesh", "Jharkhand", "West Bengal"],
            "Chhattisgarh": ["Madhya Pradesh", "Maharashtra", "Telangana", "Odisha", "Jharkhand", "Uttar Pradesh"],
            "Goa": ["Maharashtra", "Karnataka"],
            "Gujarat": ["Rajasthan", "Madhya Pradesh", "Maharashtra"],
            "Haryana": ["Punjab", "Rajasthan", "Uttar Pradesh", "Delhi", "Himachal Pradesh"],
            "Himachal Pradesh": ["Punjab", "Haryana", "Uttarakhand", "Jammu and Kashmir"],
            "Jharkhand": ["Bihar", "West Bengal", "Odisha", "Chhattisgarh", "Uttar Pradesh"],
            "Karnataka": ["Maharashtra", "Goa", "Telangana", "Andhra Pradesh", "Tamil Nadu", "Kerala"],
            "Kerala": ["Tamil Nadu", "Karnataka"],
            "Madhya Pradesh": ["Rajasthan", "Uttar Pradesh", "Chhattisgarh", "Maharashtra", "Gujarat"],
            "Maharashtra": ["Gujarat", "Madhya Pradesh", "Chhattisgarh", "Telangana", "Karnataka", "Goa"],
            "Manipur": ["Nagaland", "Assam", "Mizoram"],
            "Meghalaya": ["Assam"],
            "Mizoram": ["Assam", "Manipur", "Tripura"],
            "Nagaland": ["Arunachal Pradesh", "Assam", "Manipur"],
            "Odisha": ["West Bengal", "Jharkhand", "Chhattisgarh", "Andhra Pradesh"],
            "Punjab": ["Jammu and Kashmir", "Himachal Pradesh", "Haryana", "Rajasthan", "Chandigarh"],
            "Rajasthan": ["Punjab", "Haryana", "Uttar Pradesh", "Madhya Pradesh", "Gujarat"],
            "Sikkim": ["West Bengal"],
            "Tamil Nadu": ["Andhra Pradesh", "Karnataka", "Kerala"],
            "Telangana": ["Maharashtra", "Chhattisgarh", "Andhra Pradesh", "Karnataka"],
            "Tripura": ["Assam", "Mizoram"],
            "Uttar Pradesh": ["Uttarakhand", "Haryana", "Rajasthan", "Madhya Pradesh", "Chhattisgarh", "Jharkhand", "Bihar", "Delhi"],
            "Uttarakhand": ["Himachal Pradesh", "Uttar Pradesh"],
            "West Bengal": ["Bihar", "Jharkhand", "Odisha", "Sikkim", "Assam"],
            "Delhi": ["Haryana", "Uttar Pradesh"],
            "Jammu and Kashmir": ["Punjab", "Himachal Pradesh", "Ladakh"],
            "Ladakh": ["Jammu and Kashmir"],
            "Andaman and Nicobar Islands": [],
            "Chandigarh": ["Punjab", "Haryana"],
            "Dadra and Nagar Haveli": ["Gujarat", "Maharashtra"],
            "Lakshadweep": [],
            "Puducherry": ["Tamil Nadu"]
        }

        # Define a dictionary of prominent SEZs (can be expanded)
        self.sez_names = {
            "Andhra Pradesh": ["Brandix India Apparel City (Visakhapatnam)", "APIIC SEZs (various locations)"],
            "Gujarat": ["Dahej SEZ", "Surat Special Economic Zone", "Kandla SEZ"],
            "Telangana": ["Fab City (Hyderabad)", "GMR Hyderabad SEZ"],
            "Haryana": ["Gurgaon SEZs (various)", "Sohna SEZ"],
            "Karnataka": ["Manyata Embassy Business Park (Bengaluru - includes SEZ units)", "Electronics City (Bengaluru - has SEZ units)", "Mangalore SEZ"],
            "Punjab": ["Mohali SEZ", "Ludhiana SEZ"],
            "Tamil Nadu": ["Madras Export Processing Zone (MEPZ - Chennai)", "Nanguneri SEZ", "Sriperumbudur SEZs (various)"],
            "Uttar Pradesh": ["Noida SEZ", "Greater Noida SEZs (various)", "Moradabad SEZ"],
            "Madhya Pradesh": ["Indore SEZ"],
            "Maharashtra": ["Santacruz Electronics Export Processing Zone (SEEPZ - Mumbai)", "Navi Mumbai SEZs (various)", "Pune SEZs (various)"],
            "Odisha": ["Paradip SEZ", "Bhubaneswar SEZ"],
            "Tripura": ["Bodhjungnagar Industrial Growth Centre (includes SEZ units)"],
            "Himachal Pradesh": ["Baddi-Barotiwala-Nalagarh industrial area (includes SEZ units)"],
            "Sikkim": ["Sipahitar Industrial Growth Centre (includes SEZ units)"],
            "Dadra and Nagar Haveli": ["Silvassa SEZ"],
            "Delhi": ["Delhi SEZ"],
            "Assam": ["North East Industrial Corridor (includes SEZ components)"],
            "Kerala": ["Cochin Special Economic Zone (CSEZ)"],
            "Rajasthan": ["Jaipur SEZ", "Jodhpur SEZ"],
            "Uttarakhand": ["SIDCUL Haridwar (includes SEZ units)"],
            "West Bengal": ["Falta SEZ", "Kolkata Leather Complex (includes SEZ units)"]
            # Add more SEZ names as needed
        }

    def load_datasets(self):
        # Load electricity tariff data
        self.electricity_data = self.parse_electricity_data()

        # Load ease of doing business data
        self.business_ranking_data = self.parse_business_ranking_data()

        # Load labor data
        self.labor_data = self.parse_labor_data()

        # Load industrial zones data
        self.industrial_zones_data = self.parse_industrial_zones_data()

        # Standardize state names across datasets
        self.standardize_state_names()

    def parse_electricity_data(self):
        # Parse electricity tariff data
        data = {
            "State/UT": [
                "Andaman & Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
                "Chandigarh", "Chhattisgarh", "Dadra & Nagar Haveli", "Delhi", "Goa",
                "Gujarat", "Haryana", "Himachal Pradesh", "Jammu & Kashmir", "Jharkhand",
                "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh",
                "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
                "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim",
                "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
                "West Bengal"
            ],
            "Avg_Tariff": [
                6.75, 8.15, 5.65, 7.90, 8.21,
                6.00, 8.45, 3.75, 7.00, 4.80,
                7.52, 7.00, 4.80, 4.63, 6.50,
                8.30, 7.25, 5.75, 6.75, 7.85,
                12.50, 7.25, 6.00, 8.45, 9.45,
                5.50, 4.90, 6.89, 7.55, 4.10,
                8.55, 8.25, 6.86, 12.16, 5.65,
                7.52
            ],
            "Fixed_Charges": [
                225, 88, 0, 150, 300,
                200, 200, 150, 400, 200,
                0, 225, 150, 250, 150,
                300, 175, 225, 300, 525,
                300, 85, 225, 80, 0,
                50, 150, 125, 165, 400,
                600, 400, 75, 350, 140,
                105
            ]
        }
        df = pd.DataFrame(data)

        # Normalize tariff scores (lower is better)
        max_tariff = df["Avg_Tariff"].max()
        min_tariff = df["Avg_Tariff"].min()
        df["Electricity_Score"] = 1 - ((df["Avg_Tariff"] - min_tariff) / (max_tariff - min_tariff))

        return df

    def parse_business_ranking_data(self):
        # Parse ease of doing business data
        # This is a simplified representation based on your provided data
        data = {
            "State/UT": [
                "Andhra Pradesh", "Gujarat", "Telangana", "Haryana", "Karnataka",
                "Punjab", "Tamil Nadu", "Uttar Pradesh", "Madhya Pradesh", "Maharashtra",
                "Odisha", "Tripura", "Himachal Pradesh", "Sikkim", "Dadra & Nagar Haveli",
                "Delhi", "Assam", "Kerala", "Rajasthan", "Uttarakhand",
                "Arunachal Pradesh", "Nagaland", "Andaman & Nicobar Islands", "Lakshadweep", "Puducherry",
                "Goa", "West Bengal", "Bihar", "Chhattisgarh", "Jharkhand",
                "Manipur", "Meghalaya", "Mizoram", "Jammu & Kashmir", "Ladakh",
                "Chandigarh"
            ],
            "EODB_Score": [
                100.0, 99.73, 98.80, 98.53, 98.40,
                98.26, 97.99, 97.96, 97.82, 97.64,
                83.6, 78.8, 75.8, 71.0, 80.2,
                75.0, 75.0, 70.0, 70.0, 70.0,
                70.0, 70.0, 70.0, 70.0, 70.0,
                65.0, 65.0, 65.0, 65.0, 65.0,
                65.0, 65.0, 65.0, 65.0, 65.0,
                70.0
            ],
            "EODB_Category": [
                "Top Achiever", "Top Achiever", "Top Achiever", "Top Achiever", "Top Achiever",
                "Top Achiever", "Top Achiever", "Top Achiever", "Achiever", "Achiever",
                "Top Achiever", "Top Achiever", "Top Achiever", "Top Achiever", "Top Achiever",
                "Achiever", "Achiever", "Fast Mover", "Fast Mover", "Fast Mover",
                "Fast Mover", "Fast Mover", "Fast Mover", "Fast Mover", "Fast Mover",
                "Aspirer", "Aspirer", "Aspirer", "Aspirer", "Aspirer",
                "Aspirer", "Aspirer", "Aspirer", "Aspirer", "Aspirer",
                "Fast Mover"
            ]
        }

        df = pd.DataFrame(data)

        # Normalize EODB scores
        df["EODB_Score_Normalized"] = df["EODB_Score"] / 100.0

        return df

    def parse_labor_data(self):
        # Parse labor data
        data = {
            "State/UT": [
                "Andaman & Nicobar Islands", "Chandigarh", "Dadra & Nagar Haveli", "Delhi",
                "Jammu & Kashmir", "Ladakh", "Lakshadweep", "Puducherry", "Andhra Pradesh",
                "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
                "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
                "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
                "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
                "Sikkim", "Tamil Nadu", "Telangana", "Uttar Pradesh", "Uttarakhand",
                "West Bengal"
            ],
            "Labor_Availability": [
                "Moderate", "High", "Moderate", "High", "Moderate",
                "Low", "Low", "Moderate", "Moderate", "Moderate",
                "High", "High", "High", "Low", "Moderate",
                "Diverse", "High", "High", "High", "High",
                "Moderate", "Moderate", "Moderate", "Low", "Low",
                "Moderate", "Moderate", "Robust", "Moderate", "Low",
                "High", "Moderate", "High", "Moderate", "High"
            ],
            "Skilled_Labor_Cost": [
                845, 554, 497, 843, 483,
                575, 489, 432, 600, 220,
                483, 483, 400, 673, 700,
                373, 433, 673, 700, 800,
                580, 700, 480, 600, 510,
                210, 550, 523, 620, 535,
                650, 500, 500, 500, 600
            ],
            "Unskilled_Labor_Cost": [
                641, 544, 476, 695, 311,
                450, 401, 417, 420, 200,
                343, 447, 366, 412, 450,
                292, 366, 480, 480, 600,
                420, 500, 225, 350, 380,
                176, 450, 420, 430, 400,
                450, 433, 350, 400, 400
            ]
        }

        df = pd.DataFrame(data)

        # Create labor availability score
        availability_map = {"Low": 0.3, "Moderate": 0.6, "High": 0.9, "Diverse": 0.7, "Robust": 1.0}
        df["Labor_Availability_Score"] = df["Labor_Availability"].map(availability_map)

        # Normalize labor costs (lower is better)
        max_skilled = df["Skilled_Labor_Cost"].max()
        min_skilled = df["Skilled_Labor_Cost"].min()
        df["Skilled_Labor_Cost_Score"] = 1 - ((df["Skilled_Labor_Cost"] - min_skilled) / (max_skilled - min_skilled))

        max_unskilled = df["Unskilled_Labor_Cost"].max()
        min_unskilled = df["Unskilled_Labor_Cost"].min()
        df["Unskilled_Labor_Cost_Score"] = 1 - ((df["Unskilled_Labor_Cost"] - min_unskilled) / (max_unskilled - min_unskilled))

        # Combined labor score (availability and costs)
        df["Labor_Score"] = (df["Labor_Availability_Score"] * 0.4 +
                             df["Skilled_Labor_Cost_Score"] * 0.3 +
                             df["Unskilled_Labor_Cost_Score"] * 0.3)

        return df

    def parse_industrial_zones_data(self):
        # Create a dictionary to store zone types available in each state``
        industrial_zones = {
            "Maharashtra": ["Special Economic Zones (SEZs)", "Industrial Corridors", "National Investment and Manufacturing Zones (NIMZs)", "Industrial Parks & Clusters", "PLI Scheme Zones"],
            "Uttar Pradesh": ["Special Economic Zones (SEZs)", "Industrial Corridors", "National Investment and Manufacturing Zones (NIMZs)", "PLI Scheme Zones"],
            "Tamil Nadu": ["Special Economic Zones (SEZs)", "Industrial Corridors", "National Investment and Manufacturing Zones (NIMZs)", "PLI Scheme Zones"],
            "Kerala": ["Special Economic Zones (SEZs)"],
            "West Bengal": ["Special Economic Zones (SEZs)"],
            "Gujarat": ["Special Economic Zones (SEZs)", "Industrial Corridors", "National Investment and Manufacturing Zones (NIMZs)", "PLI Scheme Zones"],
            "Andhra Pradesh": ["Special Economic Zones (SEZs)", "Industrial Corridors", "National Investment and Manufacturing Zones (NIMZs)", "PLI Scheme Zones"],
            "Madhya Pradesh": ["Special Economic Zones (SEZs)", "Industrial Corridors", "National Investment and Manufacturing Zones (NIMZs)"],
            "Rajasthan": ["Special Economic Zones (SEZs)", "National Investment and Manufacturing Zones (NIMZs)"],
            "Odisha": ["Special Economic Zones (SEZs)", "Industrial Corridors", "National Investment and Manufacturing Zones (NIMZs)", "PLI Scheme Zones"],
            "Punjab": ["Special Economic Zones (SEZs)", "PLI Scheme Zones"],
            "Chandigarh": ["Special Economic Zones (SEZs)"],
            "Telangana": ["Special Economic Zones (SEZs)", "Industrial Corridors", "National Investment and Manufacturing Zones (NIMZs)", "Industrial Parks & Clusters", "PLI Scheme Zones"],
            "Karnataka": ["Industrial Corridors", "National Investment and Manufacturing Zones (NIMZs)", "PLI Scheme Zones"],
            "Assam": ["PLI Scheme Zones"],
            "Haryana": ["National Investment and Manufacturing Zones (NIMZs)", "PLI Scheme Zones"]
        }

        # Create a DataFrame
        states = list(industrial_zones.keys())

        # Create a DataFrame with all states/UTs and initialize with empty lists
        all_states = list(set(self.electricity_data["State/UT"].tolist()))
        data = {"State/UT": all_states}

        # Initialize zone types with empty lists for all states
        for state in all_states:
            if state not in industrial_zones:
                industrial_zones[state] = []

        # Create columns for each zone type
        for zone_type in ["Special Economic Zones (SEZs)", "Industrial Corridors",
                          "National Investment and Manufacturing Zones (NIMZs)",
                          "Industrial Parks & Clusters", "PLI Scheme Zones"]:
            data[zone_type] = [1 if zone_type in industrial_zones.get(state, []) else 0 for state in all_states]

        df = pd.DataFrame(data)

        # Calculate industrial infrastructure score
        zone_weights = {
            "Special Economic Zones (SEZs)": 0.25,
            "Industrial Corridors": 0.25,
            "National Investment and Manufacturing Zones (NIMZs)": 0.2,
            "Industrial Parks & Clusters": 0.15,
            "PLI Scheme Zones": 0.15
        }

        df["Infrastructure_Score"] = 0
        for zone_type, weight in zone_weights.items():
            df["Infrastructure_Score"] += df[zone_type] * weight

        return df

    def standardize_state_names(self):
        # Create standard state name mappings
        state_mapping = {
            "Dadra & Nagar Haveli": "Dadra and Nagar Haveli",
            "Jammu & Kashmir": "Jammu and Kashmir",
            "Andaman & Nicobar Islands": "Andaman and Nicobar Islands",
            "Uttar Pradesh (Urban)": "Uttar Pradesh"
        }

        # Apply standardization to all dataframes
        for df in [self.electricity_data, self.business_ranking_data, self.labor_data, self.industrial_zones_data]:
            df["State/UT"] = df["State/UT"].replace(state_mapping)

    def calculate_overall_score(self, industry_type, investment_scale, preferred_state=None):
        """
        Calculates the overall score for each state based on the given industry type,
        investment scale, and preferred state (if provided).  Includes proximity weighting.

        Args:
            industry_type (str): The type of industry.
            investment_scale (str): The scale of investment.
            preferred_state (str, optional): The user's preferred state. Defaults to None.

        Returns:
            pandas.DataFrame: A DataFrame with the overall scores for each state,
                              sorted in descending order.
        """
        # Get industry-specific electricity weight
        electricity_weight = self.electricity_intensity[industry_type]["electricity_weight"]

        # Get investment scale weights
        scale_weights = self.investment_scales[investment_scale]["weights"]

        # Merge all dataframes
        combined_df = self.electricity_data[["State/UT", "Avg_Tariff", "Fixed_Charges", "Electricity_Score"]]

        # Merge with business ranking data
        combined_df = pd.merge(combined_df,
                              self.business_ranking_data[["State/UT", "EODB_Score_Normalized"]],
                              on="State/UT",
                              how="left")

        # Merge with labor data
        combined_df = pd.merge(combined_df,
                              self.labor_data[["State/UT", "Labor_Score"]],
                              on="State/UT",
                              how="left")

        # Merge with industrial zones data
        combined_df = pd.merge(combined_df,
                              self.industrial_zones_data[["State/UT", "Infrastructure_Score"]],
                              on="State/UT",
                              how="left")

        # Find minimum EODB score to use for missing values
        min_eodb = self.business_ranking_data["EODB_Score_Normalized"].min()

        # Fill NaN values with lowest scores for ease of business
        combined_df["EODB_Score_Normalized"] = combined_df["EODB_Score_Normalized"].fillna(min_eodb)

        # Fill other NaN values with average scores
        for col in ["Labor_Score", "Infrastructure_Score"]:
            if combined_df[col].isna().any():
                combined_df[col] = combined_df[col].fillna(combined_df[col].mean())

        # Calculate factor-specific weighted scores
        combined_df["Weighted_Electricity"] = combined_df["Electricity_Score"] * scale_weights["electricity"] * electricity_weight
        combined_df["Weighted_EODB"] = combined_df["EODB_Score_Normalized"] * scale_weights["ease_of_business"]
        combined_df["Weighted_Labor"] = combined_df["Labor_Score"] * scale_weights["labor"]
        combined_df["Weighted_Infrastructure"] = combined_df["Infrastructure_Score"] * scale_weights["infrastructure"]

        # Calculate overall score
        combined_df["Overall_Score"] = (combined_df["Weighted_Electricity"] +
                                       combined_df["Weighted_EODB"] +
                                       combined_df["Weighted_Labor"] +
                                       combined_df["Weighted_Infrastructure"])

        # Normalize overall score
        max_score = combined_df["Overall_Score"].max()
        min_score = combined_df["Overall_Score"].min()
        combined_df["Overall_Score_Normalized"] = ((combined_df["Overall_Score"] - min_score) /
                                                  (max_score - min_score)) * 100

        # Handle preferred state if specified
        if preferred_state:
            # Make sure preferred state is included in results
            preferred_state_df = combined_df[combined_df["State/UT"].str.lower() == preferred_state.lower()]
            if len(preferred_state_df) > 0:
                # Boost score for preferred state
                combined_df.loc[combined_df["State/UT"].str.lower() == preferred_state.lower(), "Overall_Score_Normalized"] *= (1 + self.proximity_weight)

            # Apply proximity bonus to neighboring states
            preferred_state_name = preferred_state.title()  # Ensure proper capitalization
            neighbors = self.neighboring_states.get(preferred_state_name, [])
            for neighbor in neighbors:
                combined_df.loc[combined_df["State/UT"] == neighbor, "Overall_Score_Normalized"] *= (1 + self.proximity_weight)

            # Cap the score at 100
            combined_df.loc[combined_df["Overall_Score_Normalized"] > 100, "Overall_Score_Normalized"] = 100

        # Sort by overall score
        combined_df = combined_df.sort_values(by="Overall_Score_Normalized", ascending=False)

        return combined_df

    def get_industrial_zone_recommendations(self, state, industry_type):
        """
        Retrieves industrial zone recommendations for a given state and industry type,
        including specific SEZ names where available.

        Args:
            state (str): The name of the state.
            industry_type (str): The type of industry.

        Returns:
            list: A list of recommended industrial zones, with SEZ names included.
        """
        preferred_zones = self.industry_zone_preferences.get(industry_type, [])

        # Get zones available in the state
        try:
            state_row = self.industrial_zones_data[self.industrial_zones_data["State/UT"] == state]
            available_zones = []

            for zone_type in ["Special Economic Zones (SEZs)", "Industrial Corridors",
                              "National Investment and Manufacturing Zones (NIMZs)",
                              "Industrial Parks & Clusters", "PLI Scheme Zones"]:
                if state_row[zone_type].values[0] == 1:
                    available_zones.append(zone_type)

            recommended_zones = [zone for zone in preferred_zones if zone in available_zones]

            if not recommended_zones and available_zones:
                return available_zones
            elif not recommended_zones:
                return ["No specific industrial zones identified"]

            # Enhance zone names with SEZ details
            enhanced_zones = []
            for zone in recommended_zones:
                if zone == "Special Economic Zones (SEZs)":
                    sez_names = self.sez_names.get(state, [])  # Get SEZ names for the state
                    if sez_names:
                        enhanced_zones.append(f"{zone} (e.g., {', '.join(sez_names)})")
                    else:
                        enhanced_zones.append(zone)
                else:
                    enhanced_zones.append(zone)
            return enhanced_zones

        except Exception as e:
            return ["Data not available"]

    def analyze_location(self, industry_type, investment_scale, preferred_state=None):
        """
        Analyzes and recommends the top 5 states for manufacturing setup based on the
        given industry type, investment scale, and preferred state.

        Args:
            industry_type (str): The type of industry.
            investment_scale (str): The scale of investment (small, medium, large).
            preferred_state (str, optional): The user's preferred state. Defaults to None.

        Returns:
            list: A list of dictionaries, where each dictionary contains information
                  about a recommended state.
        """
        if industry_type.lower() not in self.electricity_intensity:
            return "Industry type not recognized. Please choose from: " + ", ".join(self.electricity_intensity.keys())

        if investment_scale.lower() not in self.investment_scales:
            return "Investment scale not recognized. Please choose from: " + ", ".join(self.investment_scales.keys())

        # Calculate scores
        results = self.calculate_overall_score(industry_type.lower(), investment_scale.lower(), preferred_state)

        # Get top 5 states
        top_states = results.head(5)

        # Format results for display
        formatted_results = []
        for _, row in top_states.iterrows():
            state = row["State/UT"]
            recommended_zones = self.get_industrial_zone_recommendations(state, industry_type.lower())

            formatted_results.append({
                "State/UT": state,
                "Overall Score": f"{row['Overall_Score_Normalized']:.2f}%",
                "Electricity Tariff": f"₹{row['Avg_Tariff']:.2f}/kWh",
                "Fixed Charges": f"₹{row['Fixed_Charges']}/month",
                "EODB Score": f"{row['EODB_Score_Normalized'] * 100:.2f}%",
                "Labor Score": f"{row['Labor_Score'] * 100:.2f}%",
                "Infrastructure Score": f"{row['Infrastructure_Score'] * 100:.2f}%",
                "Recommended Zones": ", ".join(recommended_zones)
            })

        return formatted_results

    
    
    
genai.configure(api_key="AIzaSyAGqVcJF4fS4Bv_ucjcwlx6chk9afziDTs")
import google.generativeai as genai

# Configure API key
genai.configure(api_key="AIzaSyAGqVcJF4fS4Bv_ucjcwlx6chk9afziDTs")
import re
import json



def get_details(industry_type, investment_scale, preferred_state, analyzer,data_list):
    model = genai.GenerativeModel('gemini-2.0-flash')

    # Extract values from analyzer
    electricity_intensity = analyzer.electricity_intensity[industry_type]['intensity']
    electricity_description = analyzer.electricity_intensity[industry_type]['description']
    investment_range = analyzer.investment_scales[investment_scale]['range']
    formatted_data = "\n".join(f"- {item}" for item in data_list)
    # Format the prompt
    prompt = f"""
You are an expert business analyst.

Please evaluate the viability of starting a business with the following parameters. Assess whether it aligns with current market trends and feasibility. Also suggest if a better location exists.
Also look up the state specific recommended locations given in extra data for analysis and then try to tell extra locations.
Here are the business details:

- Industry: {industry_type.capitalize()}
- Electricity Intensity: {electricity_intensity.capitalize()}
- Electricity Description: {electricity_description}
- Investment Scale: {investment_scale.capitalize()} ({investment_range})
- Preferred State: {preferred_state}
- extra data for analysis :{formatted_data}

Act as a business analyst and return the output in **strict JSON format only**. Analyze the viability of starting the described business, and return data in the following structured format.

Required JSON Keys:

- State/UT
- Overall Score
- Electricity Tariff
- Fixed Charges
- EODB Score
- Labor Score
- Infrastructure Score
- Recommended Zones
- Conclusion

Example:

  "State/UT": "Rajasthan",
  "Overall Score": 85,
  "Electricity Tariff": "6.5 INR/unit",
  "Fixed Charges": "Rs. 200/month",
  "EODB Score": 78,
  "Labor Score": 82,
  "Infrastructure Score": 80,
  "Recommended Zones": ["Jaipur", "Jodhpur", "Udaipur"],
  "Conclusion": "The business is viable in Rajasthan given its strong infrastructure and labor availability. However, electricity tariffs are slightly higher than the national average. Consider applying for industrial subsidy schemes."
    "preferred states": also give data for the preferred states for this and also give the zone in the preferred state Also tell about the market their
Provide a clear recommendation and reasoning. If this is not feasible, suggest an alternative state or business idea.
"""

    response = model.generate_content(prompt)
    raw_result = response.candidates[0].content.parts[0].text
    return(raw_result)


def locationfinder(industry_type=None, investment_scale=None, preferred_state=None):
    """
    Main function to run the Manufacturing Location Analyzer.
    
    Args:
        industry_type (str, optional): Type of industry for analysis
        investment_scale (str, optional): Scale of investment (low/medium/high)
        preferred_state (str, optional): Preferred state for location
        
    Returns:
        dict: Python dictionary containing analysis results and details
    """
    analyzer = ManufacturingLocationAnalyzer(proximity_weight=0.15)  # Initialize with proximity weight
    
    # Get input if not provided as parameters
    if industry_type is None:
        industry_type = input("Enter the industry type: ").lower()
    
    if investment_scale is None:
        investment_scale = input("Enter the investment scale: ").lower()

    # Get preferred state (new feature)
    if preferred_state is None:
        preferred_state = input("\nEnter preferred state (press Enter to skip): ")
        if preferred_state.strip() == "":
            preferred_state = None

    # Analyze locations
    results = analyzer.analyze_location(industry_type, investment_scale, preferred_state)
    
    # Get details - assuming this returns a JSON string with triple backticks
    details_text = get_details(industry_type, investment_scale, preferred_state, analyzer, results)
    
    # Parse the details_text if it contains JSON in triple backticks
    import re
    import json
    
    parsed_results = None
    json_pattern = r'```json\n(.*?)\n```'
    json_match = re.search(json_pattern, details_text, re.DOTALL)
    
    if json_match:
        try:
            parsed_results = json.loads(json_match.group(1))
        except json.JSONDecodeError:
            # If parsing fails, use the original text
            parsed_results = details_text
    else:
        # If no triple backticks pattern, try to parse the whole string as JSON
        try:
            parsed_results = json.loads(details_text)
        except json.JSONDecodeError:
            parsed_results = details_text  # Keep as string if parsing fails
    
    # Create a dictionary for output
    output_data = {
        "analysis_details": {
            "industry": industry_type.capitalize(),
            "electricity_intensity": analyzer.electricity_intensity[industry_type]['intensity'].capitalize(),
            "description": analyzer.electricity_intensity[industry_type]['description'],
            "investment_scale": f"{investment_scale.capitalize()} ({analyzer.investment_scales[investment_scale]['range']})",
            "preferred_state": preferred_state if preferred_state else "None"
        },
        "results": parsed_results  # Use the parsed JSON object instead of the string
    }
    
    # Return the Python dictionary directly (not a JSON string)
    return output_data

# Example usage

    

