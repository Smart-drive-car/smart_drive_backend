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



from apps.services.models import Service
from apps.shared.models import Notification
from apps.shared.push_notifications import send_notification_to_user
import logging

logger = logging.getLogger(__name__)

def check_and_send_service_warnings(car, old_mileage):
    logger.info(f"Inside check_and_send_service_warnings! Old: {old_mileage}, New: {car.current_mileage}")
    if car.current_mileage == old_mileage:
        logger.info(f"Car {car.id}: Mileage did not change. Skipping warnings.")
        return
    
    logger.info(f"Checking service warnings for Car {car.id} (Plate: {car.car_plate_number}). Old mileage: {old_mileage}, New mileage: {car.current_mileage}")

    service = Service.objects.filter(car=car, service_type__name__icontains="moy").order_by("-created_at").first()
    if not service:
        service = Service.objects.filter(car=car, service_type__name__icontains="oil").order_by("-created_at").first()
        if not service:
             service = Service.objects.filter(car=car).order_by("-created_at").first()

    if not service or service.performed_at_mileage is None or service.probeg is None:
        logger.debug(f"Car {car.id}: No valid service found with mileage and probeg. Skipping warnings.")
        return
        
    next_service_at = service.performed_at_mileage + service.probeg
    old_remaining = next_service_at - old_mileage
    new_remaining = next_service_at - car.current_mileage
    
    logger.info(f"Car {car.id}: Service {service.id}. Old remaining: {old_remaining}, New remaining: {new_remaining}")

    driver_user = car.owner.user if car.owner else None
    if not driver_user:
        logger.debug(f"Car {car.id}: No driver associated. Skipping notification.")
        return

    if old_remaining > 1000 and new_remaining <= 1000 and new_remaining > 0:
        event = "warning_1000km"
        if not Notification.objects.filter(user=driver_user, data__service_id=str(service.id), data__event=event).exists():
            logger.info(f"Car {car.id}: Triggering 1000km warning notification for User {driver_user.id}.")
            title_text = f"{int(car.current_mileage):,}km".replace(",", " ")
            body_text = f"{int(new_remaining):,}km dan so'ng moy almashtirishingiz kerak".replace(",", " ")
            send_notification_to_user(
                user=driver_user,
                title=title_text,
                body=body_text,
                data={"event": event, "service_id": str(service.id), "car_id": str(car.id)}
            )
        else:
            logger.debug(f"Car {car.id}: 1000km warning already sent for service {service.id}. Skipping.")
            
    if old_remaining >= 0 and new_remaining < 0:
        event = "warning_overdue"
        if not Notification.objects.filter(user=driver_user, data__service_id=str(service.id), data__event=event).exists():
            logger.info(f"Car {car.id}: Triggering overdue warning notification for User {driver_user.id}.")
            title_text = f"{int(car.current_mileage):,}km".replace(",", " ")
            body_text = f"Mashina probeg-ingiz taxminan: {int(car.current_mileage):,} km Agar mashina probeg-dan katta farq qilsa mashina probeg-ini kirgizishingizni so'raymiz!".replace(",", " ")
            send_notification_to_user(
                user=driver_user,
                title=title_text,
                body=body_text,
                data={"event": event, "service_id": str(service.id), "car_id": str(car.id)}
            )
        else:
            logger.debug(f"Car {car.id}: Overdue warning already sent for service {service.id}. Skipping.")
