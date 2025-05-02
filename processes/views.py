from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import ProcessRequestSerializer
from rest_framework import status
import google.generativeai as genai
import requests
import re
import json
import concurrent.futures
from .test import locationfinder

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .forms import UserRegistrationForm, UserLoginForm


from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import authenticate, login, logout
from .forms import UserRegistrationForm, UserLoginForm

# Configure API keys
genai.configure(api_key="AIzaSyAGqVcJF4fS4Bv_ucjcwlx6chk9afziDTs")
GOOGLE_PLACES_API_KEY = 'AIzaSyDkmEOj_s2bBkBVqXBR4SoUdjLLVEf1TiY'

class ProcessInfoView(APIView):
    def post(self, request):
        serializer = ProcessRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        process_name = serializer.validated_data['process_name']
        location = serializer.validated_data['location']
        
        # Get raw materials list directly from Gemini
        raw_materials = self._get_raw_materials(process_name)
        
        # Get suppliers for materials with expanded search radius if needed
        suppliers = self._get_suppliers_with_fallback(raw_materials, location)
        
        # Check which materials have suppliers and which don't
        supplied_materials = {supplier['material'] for supplier in suppliers}
        materials_without_suppliers = [m for m in raw_materials if m not in supplied_materials]
        
        # For materials without suppliers, try nearby locations
        if materials_without_suppliers:
            nearby_suppliers = self._get_nearby_suppliers(materials_without_suppliers, location)
            suppliers.extend(nearby_suppliers)
        
        return Response({
            'process': process_name,
            'location': location,
            'raw_materials': raw_materials,
            'suppliers': suppliers
        }, status=status.HTTP_200_OK)
    
    def _get_raw_materials(self, process_name):
        """Get raw materials specifically for manufacturing the product"""
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = (
            f"List ONLY the RAW MATERIALS needed to MANUFACTURE {process_name}. "
            f"Do NOT list stores, suppliers, or finished products. "
            f"Focus only on the basic input materials needed for production. "
            f"Format as a JSON array of strings. Example: ['Steel', 'Plastic']"
        )
        
        try:
            response = model.generate_content(prompt)
            result = response.candidates[0].content.parts[0].text
            
            # Try to extract JSON array first
            try:
                # Find array pattern and extract it
                match = re.search(r'\[.*\]', result, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    materials = json.loads(json_str)
                    return materials
                
            except Exception:
                # Fallback: extract materials line by line
                materials = []
                lines = result.split('\n')
                for line in lines:
                    # Remove list markers and extra spaces
                    clean_line = re.sub(r'^[-*•\d.)\s]+', '', line).strip()
                    if clean_line and len(clean_line) > 2:
                        materials.append(clean_line)
                
                return materials
        except Exception as e:
            print(f"Error getting raw materials: {e}")
            return []
    
    def _get_supplier(self, material, location, radius=25000):
        """Get suppliers for a specific material within radius"""
        try:
            response = requests.get(
                'https://maps.googleapis.com/maps/api/place/textsearch/json',
                params={
                    'query': f"{material} supplier for manufacturing in {location}",
                    'radius': radius,
                    'key': GOOGLE_PLACES_API_KEY,
                    'type': 'store|wholesale'  # Focus on actual suppliers not retail
                },
                timeout=5
            )
            
            if response.status_code != 200:
                return []
                
            places_data = response.json()
            suppliers = []
            
            for place in places_data.get('results', [])[:3]:
                suppliers.append({
                    'material': material,
                    'name': place.get('name'),
                    'rating': place.get('rating')
                })
            return suppliers
            
        except Exception as e:
            print(f"Error fetching suppliers for {material}: {e}")
            return []
    
    def _get_suppliers_with_fallback(self, materials, location):
        """Get suppliers with filtering for actual manufacturing materials"""
        all_suppliers = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_material = {
                executor.submit(self._get_supplier, material, location): material 
                for material in materials if self._is_manufacturing_material(material)
            }
            
            for future in concurrent.futures.as_completed(future_to_material):
                suppliers = future.result()
                if suppliers:  # Only add if suppliers were found
                    all_suppliers.extend(suppliers)
                
        return all_suppliers
    
    def _get_nearby_suppliers(self, materials, location):
        """Find suppliers in nearby areas for materials not found locally"""
        nearby_suppliers = []
        
        # Get geographic coordinates for the original location
        geocode_response = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={
                'address': location,
                'key': GOOGLE_PLACES_API_KEY
            }
        )
        
        geocode_data = geocode_response.json()
        if geocode_data.get('results'):
            # Get broader area to search in (state/province level)
            address_components = geocode_data['results'][0]['address_components']
            state = next((comp['long_name'] for comp in address_components 
                         if 'administrative_area_level_1' in comp['types']), '')
            country = next((comp['long_name'] for comp in address_components 
                           if 'country' in comp['types']), '')
            
            broader_location = f"{state}, {country}" if state else country
            
            # Search in broader area with increasing radius
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # Use a larger radius (100km) for the extended search
                future_to_material = {
                    executor.submit(self._get_supplier, material, broader_location, 100000): material 
                    for material in materials
                }
                
                for future in concurrent.futures.as_completed(future_to_material):
                    suppliers = future.result()
                    nearby_suppliers.extend(suppliers)
        
        return nearby_suppliers
    
    def _is_manufacturing_material(self, material):
        """Check if a material is actually a raw manufacturing material"""
        # List of keywords that might indicate finished products or services rather than raw materials
        product_keywords = ['store', 'shop', 'dealer', 'retailer', 'outlet', 'market']
        service_keywords = ['service', 'repair', 'maintenance']
        
        # Check if any keywords appear in the material name
        for keyword in product_keywords + service_keywords:
            if keyword.lower() in material.lower():
                return False
        
        return True
    

@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            form = UserRegistrationForm(data)
            
            if form.is_valid():
                user = form.save()
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                
                return JsonResponse({
                    'message': 'Registration successful',
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    },
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email
                    }
                }, status=201)
            else:
                return JsonResponse({'errors': form.errors}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
            
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            form = UserLoginForm(None, data=data)
            
            if form.is_valid():
                email = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                user = authenticate(request, username=email, password=password)
                
                if user is not None:
                    login(request, user)
                    
                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)
                    
                    return JsonResponse({
                        'message': 'Login successful',
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        },
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email
                        }
                    }, status=200)
                else:
                    return JsonResponse({'error': 'Invalid credentials'}, status=401)
            else:
                return JsonResponse({'errors': form.errors}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
            
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)


@csrf_exempt
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return JsonResponse({'message': 'Successfully logged out'}, status=200)
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

  # assuming locationfinder is your function

def analyze_view(request):
    industry = request.GET.get("industry")
    investment = request.GET.get("investment")
    state = request.GET.get("state", None)  # Optional parameter

    # Validate required parameters
    if not industry or not investment:
        return JsonResponse({
            "error": "Missing required parameters: both 'industry' and 'investment' are required."
        }, status=400)

    # Ensure valid industry and investment scale values
    valid_industries = ["textile", "electronics", "food processing", "automotive", "pharmaceutical", "chemical", "furniture", "plastics", "paper", "metal"]
    valid_investment_scales = ["small", "medium", "large"]

    if industry not in valid_industries:
        return JsonResponse({
            "error": f"Invalid industry type. Valid options are: {', '.join(valid_industries)}."
        }, status=400)
    
    if investment not in valid_investment_scales:
        return JsonResponse({
            "error": f"Invalid investment scale. Valid options are: {', '.join(valid_investment_scales)}."
        }, status=400)

    try:
        # Call your locationfinder function
        result = locationfinder(industry, investment, state)
        
        import json
        import re
        
        # Check if result is already a dictionary
        if isinstance(result, dict):
            # Special handling for the 'results' field containing JSON as a string
            if 'results' in result and isinstance(result['results'], str):
                # Extract JSON content from triple backticks if present
                json_pattern = r'```json\n(.*?)\n```'
                json_match = re.search(json_pattern, result['results'], re.DOTALL)
                
                if json_match:
                    # Replace the string with parsed JSON object
                    try:
                        parsed_json = json.loads(json_match.group(1))
                        result['results'] = parsed_json
                    except json.JSONDecodeError:
                        # If parsing fails, keep as string
                        pass
            
            response_data = result
        else:
            # If result is a string, try to parse it as JSON
            try:
                # Check if it's a string containing JSON with backticks
                json_pattern = r'```json\n(.*?)\n```'
                json_match = re.search(json_pattern, result, re.DOTALL)
                
                if json_match:
                    response_data = json.loads(json_match.group(1))
                else:
                    response_data = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                # If JSON parsing fails, return raw result with appropriate content type
                from django.http import HttpResponse
                return HttpResponse(result, content_type="application/json")
        
        # Return the result with formatted JSON (indentation for readability)
        response = JsonResponse(response_data, safe=False, json_dumps_params={"ensure_ascii": False, "indent": 2})
        
        # Ensure proper content type
        response["Content-Type"] = "application/json; charset=utf-8"
        
        return response

    except KeyError as e:
        # Specific error handling if a required key is missing in the result
        return JsonResponse({"error": f"Missing key: {str(e)}"}, status=500)

    except Exception as e:
        # General error handling
        import traceback
        error_traceback = traceback.format_exc()
        return JsonResponse({
            "error": f"An unexpected error occurred: {str(e)}",
            "traceback": error_traceback
        }, status=500)