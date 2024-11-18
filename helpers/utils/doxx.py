
import requests
from random import randint
import logging

log = logging.getLogger(__name__)

__all__ = ("get_IP_full_info", "generate_google_maps_link")

def _generate_random_first_number(excluded_ranges):
	while True:
		# Generate a random number between 1 and 223 (inclusive)
		random_int = randint(1, 223)

		# Check if the random number falls within any of the excluded ranges
		if not any(isinstance(excluded, int) and excluded == random_int or
					isinstance(excluded, tuple) and excluded[0] <= random_int <= excluded[1]
					for excluded in excluded_ranges):
			return random_int

def _generate_random_IP():
	# Example usage:
	excluded_first = [10, 127, 169, 172, 192, (224, 255)]  # Define excluded ranges as list of tuples

	a = _generate_random_first_number(excluded_first)
	b = randint(1, 254)
	c = randint(1, 254)
	d = randint(1, 254)

	return f"{str(a)}.{str(b)}.{str(c)}.{str(d)}"

def _get_ip_geolocation(ip_address):
	my_key = "FEF58E00F36E918AC646F3BAF5F60F30"
	# Construct the API request URL
	api_url = f"https://api.ip2location.io/?key={my_key}&ip={ip_address}"

	# Send an HTTP GET request to the API
	response = requests.get(api_url)

	# Check if the request was successful (Status code 200)
	if response.status_code == 200:
		# Parse the JSON response
		data = response.json()
		latitude = data['latitude'] or "*no data found*"
		longitude = data['longitude'] or "*no data found*"
		timezone = data['time_zone'] or "*no data found*"
		auto_sys_number = data['asn'] or "*no data found*"
		auto_sys = data['as'] or "*no data found*"
		is_proxy = data['is_proxy'] or "*no data found*"
		return latitude, longitude, timezone, auto_sys_number, auto_sys, is_proxy
	else:
		log.error(f"Failed to fetch geolocation information. Status code: {response.status_code}")
		return 44.9573, -93.0515, "-05:00", "5079", "T-Mobile USA Inc.", False

def get_IP_full_info():
	ip_address = _generate_random_IP()
	latitude, longitude, timezone, auto_sys_number, auto_sys, is_proxy = _get_ip_geolocation(ip_address)
	my_api_key = "eb584ff302804cdf8eb6df139370104e"
	url = f"https://api.geoapify.com/v1/geocode/reverse?lat={latitude}&lon={longitude}&format=json&apiKey={my_api_key}"

	response = requests.get(url)
	response_json = response.json()

	if "results" in response_json:
		result = response_json["results"][0]

		country = result.get("country", "*no data found*")
		country_code = result.get("country_code", "*no data found*")
		state = result.get("state", "*no data found*")
		county = result.get("county", "*no data found*")
		city = result.get("city", "*no data found*")
		postcode = result.get("postcode", "*no data found*")
		district = result.get("district", "*no data found*")
		suburb = result.get("suburb", "*no data found*")
		street = result.get("street", "*no data found*")
		house_number = result.get("housenumber", "*no data found*")
		state_code = result.get("state_code", "*no data found*")
		result_type = result.get("result_type", "*no data found*")

	else:
		ip_address = "174.157.71.171"
		latitude = 44.9573
		longitude = -93.0515
		timezone = "-05:00"
		auto_sys_number = "5079"
		auto_sys = "T-Mobile USA Inc."
		is_proxy = False
		country = "United States"
		country_code = "us"
		state = "Minnesota"
		county = "Ramsey County"
		city = "St. Paul"
		postcode = "55106"
		district = "St. Paul"
		suburb = "Dayton's Bluff"
		street = "Hancock Street"
		house_number = "1167"
		state_code = "MN"
		result_type = "building"
		return False

	return ip_address, latitude, longitude, timezone, auto_sys_number, auto_sys, is_proxy, country, country_code, \
		state, county, city, postcode, district, suburb, street, house_number, state_code, result_type

def generate_google_maps_link(latitude, longitude):
	if latitude > 0:
		lat_dir = "N"
	else:
		lat_dir = "S"
		latitude *= -1

	if longitude > 0:
		lng_dir = "E"
	else:
		lng_dir = "W"
		longitude *= -1

	latitude_degrees = int(latitude)

	latitude_minutes_temp = (latitude - latitude_degrees) * 60
	latitude_minutes = int(latitude_minutes_temp)

	latitude_seconds_temp = (latitude_minutes_temp - latitude_minutes) * 60
	latitude_seconds = round(latitude_seconds_temp, 1)

	longitude_degrees = int(longitude)

	longitude_minutes_temp = (longitude - longitude_degrees) * 60
	longitude_minutes = int(longitude_minutes_temp)

	longitude_seconds_temp = (longitude_minutes_temp - longitude_minutes) * 60
	longitude_seconds = round(longitude_seconds_temp, 1)

	lat_cvt = f"{latitude_degrees}°{latitude_minutes}'{latitude_seconds}\"{lat_dir}"
	lng_cvt = f"{longitude_degrees}°{longitude_minutes}'{longitude_seconds}\"{lng_dir}"

	prefix = "https://www.google.com/maps/place/"
	data = "data=!3m1!4b1!4m4!3m3!8m2!3d"
	postfix = "?entry=ttu"

	return f"{prefix}{lat_cvt}+{lng_cvt}/@{latitude},{longitude},17z/{data}{latitude}!4d{longitude}{postfix}"
