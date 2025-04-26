from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import ProcessRequestSerializer
from rest_framework import status
import google.generativeai as genai
import requests
import re

genai.configure(api_key="AIzaSyAGqVcJF4fS4Bv_ucjcwlx6chk9afziDTs")
GOOGLE_PLACES_API_KEY='AIzaSyDkmEOj_s2bBkBVqXBR4SoUdjLLVEf1TiY'
# Create your views here.
class ProcessInfoView(APIView):
    def post(self,request):
        serializer= ProcessRequestSerializer(data=request.data)
        print("Incoming data:", request.data)
        if serializer.is_valid():
            print("Serializer is valid ✅")  
            
            process_name= serializer.validated_data['process_name']
            location=serializer.validated_data['location']
            model=genai.GenerativeModel('gemini-2.0-flash')
            prompt = (f"What are the raw materials and necessary parameters required for the {process_name} process in textile manufacturing? "
            )

            response =model.generate_content(prompt)
            gemini_result=response.candidates[0].content.parts[0].text

            raw_materials = re.findall(r'(?i)\b[A-Z][a-z]+\b', gemini_result)
            raw_materials = list(set(raw_materials))
            suppliers=[]
            for material in raw_materials:
                try:
                    places_response=requests.get(
                         'https://maps.googleapis.com/maps/api/place/textsearch/json',
                         
                        params={
                            'query':f"{material} supplier in {location}",
                            'radius':50000,
                            'key':GOOGLE_PLACES_API_KEY
                        }
                    )
                    places_data=places_response.json()
                    if places_data.get('results'):
                        for place in places_data['results']:
                            suppliers.append({
                                'material': material,
                                'name': place.get('name'),
                                'address': place.get('formatted_address'),
                                'location': place.get('geometry', {}).get('location'),
                                'rating': place.get('rating'),
                                'user_ratings_total': place.get('user_ratings_total'),
                            })
                except Exception as e:
                    print(f"Error fetching suppliers for {material}: {e}")

            return Response({
                'process': process_name,
                'location': location,
                'raw_materials': raw_materials,
                'details': gemini_result,
                'suppliers': suppliers
            }, status=status.HTTP_200_OK)

        print("Serializer errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

           
           
