export type EligibilityStatus = 'eligible' | 'not-eligible' | 'partial';

export interface TenderRequirement {
  id: string;
  label: string;
  matched: boolean;
  category: string;
}

export interface TenderDocument {
  id: string;
  name: string;
  required: boolean;
}

export interface Tender {
  id: string;
  title: string;
  organization: string;
  industry: string;
  location: string;
  budget: number;
  budgetLabel: string;
  deadline: string;
  daysLeft: number;
  matchPercentage: number;
  category: string;
  description: string;
  eligibilityStatus: EligibilityStatus;
  aiSummary: string;
  requirements: TenderRequirement[];
  documents: TenderDocument[];
  referenceNo: string;
  publishedDate: string;
  coverLetter?: string;
}

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  uploadDate: string;
}

export interface CompanyProfile {
  name: string;
  industries: string[];
  location: string;
  budgetRange: string;
}

export interface AppNotification {
  id: string;
  type: 'deadline' | 'match';
  heading: string;
  message: string;
  tenderId: string;
  read: boolean;
}
