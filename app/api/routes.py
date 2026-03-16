from fastapi import APIRouter
from app.services.extractor_service import ExtractorService
from app.services.filter_service import FilterService
from app.services.timeline_service import TimelineService
from app.services.eureka_service import EurekaService

router = APIRouter()
extractor = ExtractorService()
filter_service = FilterService()
timeline_service = TimelineService()
eureka_service = EurekaService()


@router.post("/generate-postmortem/{incident_sys_id}")
def generate_postmortem(incident_sys_id: str):
    package = extractor.extract_incident_package(incident_sys_id)

    filtered_notes = filter_service.classify_and_filter(package.work_notes + package.comments)
    timeline = timeline_service.build_timeline(package.audit_events, filtered_notes)
    mttr_minutes = timeline_service.calculate_mttr_minutes(package.incident)
    eureka = eureka_service.detect_eureka_event(timeline)

    return {
        "incident_number": package.incident.number,
        "mttr_minutes": mttr_minutes,
        "timeline_count": len(timeline),
        "eureka_timestamp": eureka.timestamp if eureka else None,
        "eureka_note": eureka.content if eureka else None,
    }

#  Health of the end point
@router.get("/health")
def health():
    return {"status": "ok"}