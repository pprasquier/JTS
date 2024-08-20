from typing import List, Optional
from langchain_core.pydantic_v1 import BaseModel, Field


class BaseModel(BaseModel):
    def __repr__(self):
        return f"{self.__class__.__name__}({self.dict()})"


class JobCharacteristics(BaseModel):
    organization: Optional[str] = Field(description="Name of the organization) company offering the job")
    position: Optional[str] = Field(description="Position")
    location: Optional[str] = Field(description="Location")
    product:Optional[str] = Field(description="Name of the product or project")
    organizationdetails: Optional[str] = Field(description="Description of what the organization/company does")
    responsibilities:Optional[List[str]] = Field(description="Responsibilities")
    requirements:Optional[List[str]] = Field(description="Requirements for the position")
    benefits:Optional[List[str]] = Field(description="Benefits included with the position")
    salary:Optional[str] = Field(description="Salary range")
    applicationprocess:Optional[str] = Field(description="Steps required to be able to apply")
    recruitername:Optional[str] = Field(description="Name of the person handling the recruitment")
    recruitercontact:Optional[str] = Field(description="Contact of the person handling the recruitment")

class Insight(BaseModel):
    insight: str = Field(description="Description of the insight.")
    messaging:str = Field(description="How the this insight is relevant to the underlying point in the context of a job application.")
    type: str = Field(description="Where the insight comes from.E.g. 'Professional expeience', 'Personal project', 'Q&A'")
    context: Optional[str] = Field(description="Context (company/institution name, period, etc.) of the insight. E.g.: 'Walmart', 'Teenage years'...")
    relevancescore: Optional[int] = Field(description="From 1 (lowest) to 10 (highest): how relevant is this insight for the underlying salient point.")

class SalientPoint(BaseModel):
    point: str = Field(description="Description of the salient point.")
    category: Optional[str] = Field(description="Category of the salient point.")
    importancescore: Optional[int] = Field(description="From 1 (lowest) to 10 (highest): how important is that point for the overall job offer.")

class RelevantInsights(BaseModel):
    insights: List[Insight] = Field(description="Relevant insights for the salient point.")
    
class SalientPointWithInsights(SalientPoint):
        insights: Optional[List[Insight]] = Field(description="Relevant insights for the salient point.")

class CoverLetter(BaseModel):
    current_body: Optional[str] = Field(description="Current cover letter content.")
    to: Optional[str] = Field(description="Recipient of the cover letter.")
    file_name:Optional[str] = Field(description="Name of the cover letter file.")
    directory: Optional[str] = Field(description="Path to the job application directory.")

class ApplicationStatus(BaseModel):
    has_raw_post: bool = Field(default=False, description="Whether the application has a raw post.")
    is_parsed: bool = Field(default=False, description="Whether the application has been parsed.")
    has_salient_points: bool = Field(default=False, description="Whether the application has salient points")
    has_relevant_insights: bool = Field(default=False, description="Whether the application has relevant insights")
    has_cover_letter: bool = Field(default=False, description="Whether the application has a cover letter")
    has_custom_summary: bool = Field(default=False, description="Whether the application has a custom summary.")
    
class Contact(BaseModel):
    full_name: str = Field(description="Full name of the individual.")
    phone: Optional[str] = Field(description="Phone number of the individual.")
    email: Optional[str] = Field(description="Email address of the individual.")
    location: Optional[str] = Field(description="Location of the individual.")
    summary: Optional[str] = Field(description="Professional summary of the individual.")

class Language(BaseModel):
    language: str = Field(description="Language spoken by the individual.")
    proficiency: Optional[str] = Field(description="Proficiency of the individual in the language.")

class Certification(BaseModel):
    issuer: str = Field(description="Name of the certification issuer.")
    certification: str = Field(description="Name of the certification.")
    
class Experience(BaseModel):
    organization: str = Field(description="Name of the organization.")
    type: Optional[str] = Field(description="Type of experience (education, professional, personal, etc.).")
    url: Optional[str] = Field(description="URL of the organization.")
    start_year: Optional[int] = Field(description="Starting year e of the experience.")
    end_year: Optional[int] = Field(description="Ending year of the experience.")
    start_month: Optional[int] = Field(description="Starting month e of the experience.")
    end_month: Optional[int] = Field(description="Ending month of the experience.")
    location: Optional[str] = Field(description="Location of the experience.")
    position: Optional[str] = Field(description="Position held at the organization.")
    organization_details: Optional[str] = Field(description="Description of what the organization does.")
    skills: Optional[List[str]] = Field(description="Skills acquired at the organization.")
    responsibilities: Optional[List[str]] = Field(description="Responsibilities at the organization.")
    
class Resume(BaseModel):
    contact:Optional[Contact] = Field(description="Contact information of the individual.")
    experiences: Optional[List[Experience]] = Field(description="List of experiences of the individual.")
    languages: Optional[List[Language]] = Field(description="List of languages spoken by the individual.")
    certifications: Optional[List[Certification]] = Field(description="List of certifications acquired by the individual.")