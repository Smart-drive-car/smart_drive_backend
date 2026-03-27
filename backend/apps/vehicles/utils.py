import math

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers

    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    
    a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) * math.sin(dLon / 2))
         
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance # Returns distance in kilometers

def clean_gps_points(points):
    """
    Cleans GPS points by removing those with high inaccuracy or impossible speeds.
    """
    cleaned = []
    for i in range(len(points)):
        point = points[i]
        
        # 1. Reject points with terrible accuracy (e.g., > 40 meters margin of error)
        if point.get('accuracy', 0) > 40:
            continue
            
        # 2. Reject impossible speeds directly reported by GPS (assuming Flutter sends m/s).
        # 160 km/h is ~44.4 m/s. We drop anything above this to prevent glitches.
        if point.get('speed', 0) > 44.4:
            continue
            
        cleaned.append(point)
        
    return cleaned

def calculate_total_distance(points):
    """
    Calculates total distance by summing the Haversine distance between consecutive points.
    Filters out jumps by calculating the point-to-point speed and ensuring it's between 15 km/h and 160 km/h.
    """
    total_km = 0.0
    for i in range(1, len(points)):
        prev = points[i-1]
        curr = points[i]
        
        dist_km = calculate_haversine_distance(
            prev['lat'], prev['lng'],
            curr['lat'], curr['lng']
        )
        
        # Calculate time difference in hours based on the timestamp
        time_diff_seconds = (curr['timestamp'] - prev['timestamp']).total_seconds()
        
        if time_diff_seconds > 0:
            time_diff_hours = time_diff_seconds / 3600.0
            speed_kmh = dist_km / time_diff_hours
            
            # Only accumulate mileage if the calculated speed is between 15 km/h and 160 km/h
            if 15 <= speed_kmh <= 160:
                total_km += dist_km
        
    return total_km
