import { useEffect, useMemo, useRef, useState } from "react";

type Role = "bot" | "user";
type Language = "en" | "de";
type ViewMode = "customer" | "developer";

type Message = {
  id: number;
  role: Role;
  html: string;
};

type Requirements = {
  initialNeed?: string;
  application?: string;
  productDomain?: string;
  catalogCategory?: string;
  genericInterface?: string;
  supportRequested?: boolean;
  supportGoal?: string;
  supportProduct?: string;
  supportTopic?: string;
  designSituation?: string;
  existingComponent?: string;
  specialRequirements?: string;
  targetVolume?: string;
  projectTimeline?: string;
  projectPartners?: string;
  technologies?: string[];
  positioning?: "yes" | "no";
  cellularClass?: string;
  region?: string;
  architecture?: string;
  antenna?: string;
  wifiGeneration?: string[];
  gnssPrecision?: string;
  lowPower?: boolean;
  hostInterface?: string;
  antennaConnector?: string;
  antennaCount?: string;
  antennaApplication?: string;
  antennaBand?: string;
  antennaActive?: string;
  bluetoothRequirement?: string;
  maxFootprint?: string;
  formFactor?: string;
  gnssDualBand?: string;

  // Universal schema-driven engineering requirements.
  engineering?: Record<string, string | number | boolean>;
  answeredEngineering?: string[];

  // Capacitor-specific engineering requirements.
  capacitorCapacitance?: string;
  capacitorVoltage?: string;
  capacitorTechnology?: string;
  capacitorMounting?: string;
  capacitorTolerance?: string;
  capacitorCaseSize?: string;
  capacitorEsrMax?: string;
  capacitorRippleMin?: string;
  capacitorLifetimeMin?: string;
  capacitorTemperatureRange?: string;
  capacitorEnergyMin?: string;
};

type QuestionKey =
  | "initialNeed"
  | "productDomain"
  | "catalogCategory"
  | "genericInterface"
  | "application"
  | "supportRequested"
  | "supportGoal"
  | "supportProduct"
  | "supportTopic"
  | "designSituation"
  | "existingComponent"
  | "specialRequirements"
  | "targetVolume"
  | "projectTimeline"
  | "projectPartners"
  | "technologies"
  | "positioning"
  | "lowPower"
  | "cellularClass"
  | "region"
  | "architecture"
  | "antenna"
  | "wifiGeneration"
  | "gnssPrecision"
  | "hostInterface"
  | "antennaConnector"
  | "antennaCount"
  | "antennaApplication"
  | "antennaGnssBand"
  | "antennaWifiBand"
  | "antennaActive"
  | "bluetoothRequirement"
  | "maxFootprint"
  | "formFactor"
  | "gnssDualBand"
  | "capacitorCapacitance"
  | "capacitorVoltage"
  | "capacitorTechnology"
  | "capacitorMounting"
  | "capacitorTolerance"
  | "capacitorCaseSize"
  | "capacitorEsrMax"
  | "capacitorRippleMin"
  | "capacitorLifetimeMin"
  | "capacitorTemperatureRange"
  | "capacitorEnergyMin"
  | `engineering:${string}`;

type Option = {
  label: string;
  value: string | boolean | string[];
};

type AdaptiveQuestionResponse = {
  candidate_count: number;
  evaluated_fields: number;
  question?: {
    key: QuestionKey;
    text: string;
    options: Option[];
    multi_select: boolean;
    required: boolean;
    information_gain: number;
    known_coverage: number;
    candidate_count: number;
    distinct_known_values: number;
    mode: "qualification" | "tie_break";
    top_tie_count: number;
  } | null;
};

type ProductFeatures = {
  technologies: string[];
  cellular_class?: string | null;
  region?: string | null;
  has_gnss?: boolean | null;
  gnss_precision?: string | null;
  wifi_generation?: string | null;
  has_bluetooth?: boolean | null;
  architecture?: string | null;
  antenna?: string | null;
  form_factor?: string | null;
  antenna_applications?: string[];
  antenna_bands?: string[];
  antenna_active?: boolean | null;
  engineering?: Record<string, string | number | boolean | string[]>;
  temperature_min?: number | null;
  temperature_max?: number | null;
  certifications: string[];
  documents_url: string;
  request_url: string;
  imported_live: boolean;
  capacitance_uf?: number | null;
  capacitor_voltage_v?: number | null;
  capacitor_tolerance_pct?: number | null;
  capacitor_technology?: string | null;
  capacitor_mounting?: string | null;
  capacitor_case_size?: string | null;
  capacitor_esr_ohm?: number | null;
  capacitor_ripple_current_a?: number | null;
  capacitor_lifetime_h?: number | null;
  capacitor_theoretical_energy_j?: number | null;
};

type Product = {
  id: number;
  part_number: string;
  manufacturer: string;
  category: string;
  description: string;
  tags: string[];
  product_url: string;
  lifecycle: string;
  availability: string;
  features?: ProductFeatures | null;
};

type MatchCriterionEvidence = {
  key: string;
  label: string;
  requested_value: string;
  status: "verified" | "inferred" | "not_verified" | "conflicting";
  evidence_value?: string | null;
  source_type?: string | null;
  source_title?: string | null;
  source_url?: string | null;
  page_number?: number | null;
  confidence?: number | null;
};

type MatchEvidenceSummary = {
  total: number;
  verified: number;
  inferred: number;
  not_verified: number;
  conflicting: number;
  evidence_score: number;
};

type ProductFamilySummary = {
  id: number;
  name: string;
  manufacturer: string;
  category: string;
  verification_status: string;
  source_type: string;
  confidence: number;
  member_count: number;
};

type Match = {
  product: Product;
  family?: ProductFamilySummary | null;
  match_percent: number;
  solution_scope_score: number;
  extra_technologies: string[];
  recommendation_confidence:
    | "verified_fit"
    | "provisional_fit"
    | "fae_verification_required";
  recommendation_confidence_label: string;
  verification_required: boolean;
  verification_issues: string[];
  reasons: string[];
  evidence_score: number;
  evidence_summary: MatchEvidenceSummary;
  criterion_evidence: MatchCriterionEvidence[];
};

type MatchResponse = {
  count: number;
  matches: Match[];
};

type RequirementInterpretResponse = {
  requirements: {
    application?: string | null;
    product_domain?: string | null;
    catalog_category?: string | null;
    generic_interface?: string | null;
    technologies: string[];
    cellular_class?: string | null;
    region?: string | null;
    architecture?: string | null;
    antenna?: string | null;
    wifi_generation?: string[] | null;
    gnss_precision?: string | null;
    low_power?: boolean | null;
    host_interface?: string | null;
    antenna_connector?: string | null;
    antenna_count?: number | null;
    antenna_application?: string | null;
    antenna_band?: string | null;
    antenna_active?: boolean | null;
    bluetooth_required?: boolean | null;
    bluetooth_version_min?: string | null;
    max_footprint_mm2?: number | null;
    form_factor?: string | null;
    gnss_dual_band?: boolean | null;
    engineering_requirements?: Record<string, string | number | boolean>;
    answered_engineering_fields?: string[];
    capacitance_uf?: number | null;
    capacitor_voltage_v?: number | null;
    capacitor_tolerance_pct?: number | null;
    capacitor_tolerance_open?: boolean;
    capacitor_technology?: string | null;
    capacitor_mounting?: string | null;
    capacitor_case_size?: string | null;
    capacitor_esr_max_ohm?: number | null;
    capacitor_ripple_current_min_a?: number | null;
    capacitor_lifetime_min_h?: number | null;
    capacitor_temperature_min_c?: number | null;
    capacitor_temperature_max_c?: number | null;
    capacitor_energy_min_j?: number | null;
  };
  evidence: string[];
  confidence: number;
  missing: string[];
  next_question?: {
    key: string;
    text: string;
    options: string[];
  } | null;
};

const API =
  import.meta.env.VITE_API_URL ??
  (import.meta.env.DEV ? "http://localhost:8000" : "");

const tr = (language: Language, en: string, de: string) => language === "de" ? de : en;

const LABELS_DE: Record<string, string> = {
  productDomain: "Produktbereich",
  catalogCategory: "Produkttyp",
  genericInterface: "Schnittstelle",
  application: "Anwendung",
  supportRequested: "SE Unterstützung",
  supportGoal: "Nächster Schritt",
  supportProduct: "Produkt für Follow-up",
  supportTopic: "FAE-Fokus",
  designSituation: "Projektsituation",
  existingComponent: "Bestehende Komponente",
  specialRequirements: "Besondere Anforderungen",
  targetVolume: "Jahresmenge",
  projectTimeline: "Projektphase",
  projectPartners: "Projektpartner",
  technologies: "Technologie",
  positioning: "Positionierung",
  lowPower: "Low Power",
  cellularClass: "Mobilfunkklasse",
  region: "Region",
  architecture: "Architektur",
  antenna: "Antenne",
  wifiGeneration: "Wi-Fi Generation",
  gnssPrecision: "GNSS Genauigkeit",
  hostInterface: "Host-Schnittstelle",
  antennaConnector: "Antennenanschluss",
  antennaCount: "Antennenanschlüsse",
  antennaApplication: "Antennenanwendung",
  antennaGnssBand: "GNSS-Antennenband",
  antennaWifiBand: "Wi-Fi- / Bluetooth-Band",
  antennaBand: "Antennenband",
  antennaActive: "GNSS-Antennentyp",
  bluetoothRequirement: "Bluetooth-Anforderung",
  maxFootprint: "Maximale Fläche",
  formFactor: "Bauform",
  gnssDualBand: "GNSS-Bänder",
  capacitorCapacitance: "Kapazität",
  capacitorVoltage: "Nennspannung",
  capacitorTechnology: "Kondensatortechnologie",
  capacitorMounting: "Montage",
  capacitorTolerance: "Toleranz",
  capacitorCaseSize: "Baugröße",
  capacitorEsrMax: "Max. ESR",
  capacitorRippleMin: "Min. Ripple-Strom",
  capacitorLifetimeMin: "Min. Lebensdauer",
  capacitorTemperatureRange: "Temperaturbereich",
  capacitorEnergyMin: "Min. Energie",
};

const OPTION_DE: Record<string, string> = {
  "Connectivity / Wireless": "Konnektivität / Funk",
  "GNSS / Positioning": "GNSS / Positionierung",
  "Sensors": "Sensoren",
  "Antennas / RF": "Antennen / HF",
  "Displays / HMI": "Displays / HMI",
  "Storage": "Speicher",
  "Timing": "Timing",
  "Embedded Computing": "Embedded Computing",
  "Components / EMC": "Komponenten / EMV",
  "Audio / Haptics": "Audio / Haptik",

  "Motion Sensors": "Bewegungssensoren",
  "Pressure Sensors": "Drucksensoren",
  "Force Sensors": "Kraftsensoren",
  "Airflow Sensors": "Durchflusssensoren",
  "Humidity Sensors": "Feuchtigkeitssensoren",
  "Temperature Sensors": "Temperatursensoren",
  "Hall / Magnetic Sensors": "Hall- / Magnetsensoren",
  "Gas Sensors": "Gassensoren",
  "External Antennas": "Externe Antennen",
  "SMD Antennas": "SMD-Antennen",
  "Embedded Antennas": "Embedded-Antennen",
  "Other RF Components": "Weitere HF-Komponenten",
  "TFT Displays": "TFT-Displays",
  "OLED Displays": "OLED-Displays",
  "Character Displays": "Zeichendisplays",
  "Graphic Displays": "Grafikdisplays",
  "Smart Displays": "Smart Displays",
  "Display Driver IC": "Display-Treiber-IC",
  "Flash Storage": "Flash-Speicher",
  "Embedded Peripherals": "Embedded-Peripherie",
  "Real-Time Clocks (RTCs)": "Echtzeituhren (RTCs)",
  "Oscillators": "Oszillatoren",
  "Timing IC": "Timing-IC",
  "Crystals": "Quarze",
  "Computer on Modules": "Computer-on-Modules",
  "Single Board Computer": "Single-Board-Computer",
  "Capacitors": "Kondensatoren",
  "Relays": "Relais",
  "Contactors": "Schütze",
  "Switches": "Schalter",
  "Connectors": "Steckverbinder",
  "Chokes": "Drosseln",
  "EMI / EMC Filters": "EMI- / EMV-Filter",
  "EMI Accessories": "EMI-Zubehör",
  "Vibration / Haptics": "Vibration / Haptik",
  "Audio Codecs": "Audio-Codecs",

  "Cellular": "Mobilfunk",
  "Bluetooth LE": "Bluetooth LE",
  "Bluetooth": "Bluetooth",
  "Wi-Fi": "Wi-Fi",
  "GNSS": "GNSS",
  "Small size": "Kleine Baugröße",
  "Battery powered / Low power": "Batteriebetrieb / Low Power",
  "Extended temperature range": "Erweiterter Temperaturbereich",
  "No special requirements": "Keine besonderen Anforderungen",
  "Analog output": "Analogausgang",
  "Digital output": "Digitalausgang",
  "No preference / not sure": "Keine Präferenz / noch offen",
  "Either is acceptable": "Beides ist geeignet",
  "Version open / not sure": "Version offen / noch unklar",
  "Yes — version open / not sure": "Ja — Version offen / noch unklar",
  "Not required": "Nicht erforderlich",
  "Bluetooth LE 5.0 or newer": "Bluetooth LE 5.0 oder neuer",
  "Bluetooth LE 5.1 or newer": "Bluetooth LE 5.1 oder neuer",
  "Bluetooth LE 5.2 or newer": "Bluetooth LE 5.2 oder neuer",
  "Bluetooth LE 5.3 or newer": "Bluetooth LE 5.3 oder neuer",
  "Bluetooth LE 5.4 or newer": "Bluetooth LE 5.4 oder neuer",
  "Bluetooth LE 6.0 or newer": "Bluetooth LE 6.0 oder neuer",
  "Standard GNSS / meter-level": "Standard-GNSS / Meterbereich",
  "High precision / centimeter-level (RTK)": "Hochpräzise / Zentimeterbereich (RTK)",
  "No fixed accuracy / not sure": "Keine feste Genauigkeit / noch unklar",
  "L1 is sufficient": "L1 ist ausreichend",
  "Dual-band L1 + L5 required": "Dual-Band L1 + L5 erforderlich",
  "Ceramic / MLCC": "Keramik / MLCC",
  "Tantalum": "Tantal",
  "Film": "Folie",
  "Aluminum electrolytic": "Aluminium-Elektrolyt",
  "Polymer": "Polymer",
  "Supercapacitor": "Superkondensator",
  "SMD / SMT": "SMD / SMT",
  "Through-hole": "THT / bedrahtet",
  "No preference": "Keine Präferenz",
  "Yes": "Ja",
  "No": "Nein",
  "Yes, GNSS positioning": "Ja, GNSS-Positionierung",
  "New design": "Neues Design",
  "Replacement / redesign": "Ersatz / Redesign",
  "Not sure yet": "Noch offen",
  "Yes, continue with project details": "Ja, Projektdetails ergänzen",
  "No, the product recommendation is enough": "Nein, die Produktempfehlung reicht aus",
  "Technical review with an SE FAE": "Technische Prüfung mit einem SE FAE",
  "Price / availability / samples": "Preis / Verfügbarkeit / Muster",
  "No — the recommendation is enough": "Nein — die Empfehlung reicht aus",
  "Compare the top candidates": "Top-Kandidaten vergleichen",
  "Validate the recommendation": "Empfehlung validieren",
  "Hardware / interface integration": "Hardware- / Schnittstellenintegration",
  "Antenna / RF": "Antenne / HF",
  "Firmware / software": "Firmware / Software",
  "Certification / regulatory": "Zertifizierung / Regulierung",
  "Prototype / samples now": "Prototyp / Muster jetzt",
  "Within 3 months": "Innerhalb von 3 Monaten",
  "3–6 months": "3–6 Monate",
  "More than 6 months": "Mehr als 6 Monate",
  "GNSS": "GNSS",
  "Wi-Fi / Bluetooth": "Wi-Fi / Bluetooth",
  "Cellular / LTE / 5G": "Mobilfunk / LTE / 5G",
  "ISM / LPWAN (433 / 868 / 915 MHz)": "ISM / LPWAN (433 / 868 / 915 MHz)",
  "Multi-radio / combination": "Multi-Radio / Kombination",
  "GNSS L1": "GNSS L1",
  "GNSS multi-band (L1 + L2/L5)": "GNSS Multi-Band (L1 + L2/L5)",
  "No fixed band / not sure": "Kein festes Band / noch offen",
  "2.4 GHz": "2,4 GHz",
  "2.4 + 5 GHz": "2,4 + 5 GHz",
  "6 GHz / Wi-Fi 6E capable": "6 GHz / Wi-Fi 6E-fähig",
  "Active antenna": "Aktive Antenne",
  "Passive antenna": "Passive Antenne",
  "Development service provider": "Entwicklungsdienstleister",
  "Manufacturer / EMS": "Hersteller / EMS",
  "EMC laboratory": "EMV-Labor",
  "None yet": "Noch keine",
  "Development": "Entwicklung",
  "Prototypes": "Prototypen",
  "Pre-series": "Vorserie",
  "Series production": "Serienproduktion",
  "Not defined yet": "Noch nicht definiert",
};

function localizeOption(option: Option, language: Language): Option {
  if (language === "en") return option;
  return { ...option, label: OPTION_DE[option.label] ?? option.label };
}

function localizeOptions(options: Option[] | undefined, language: Language): Option[] {
  return (options ?? []).map((option) => localizeOption(option, language));
}

function localizeQuestion(
  question: { key: QuestionKey; text: string; options?: Option[] } | null,
  language: Language
) {
  if (!question) return null;
  if (language === "en") return question;

  const exact: Record<string, string> = {
    "I am the SE Product Assistant. How can I help you?<br><span class='botHint'>Briefly describe the application, component, or technical requirement you are looking for.</span>":
      "Wie kann ich Ihnen helfen?<br><span class='botHint'>Beschreiben Sie kurz Ihre Anwendung, die gesuchte Komponente oder Ihre technische Anforderung.</span>",
    "Which product area best matches what you are looking for?":
      "Welcher Produktbereich passt am besten zu Ihrer Anforderung?",
    "Which connectivity / positioning technologies are required? You can select more than one.":
      "Welche Funk- bzw. Positionierungstechnologien werden benötigt? Sie können mehrere auswählen.",
    "Do you have a preferred electrical interface or sensor output?":
      "Bevorzugen Sie eine bestimmte elektrische Schnittstelle bzw. einen Sensorausgang?",
    "Are there any important design constraints or special requirements?":
      "Gibt es wichtige Designvorgaben oder besondere Anforderungen?",
    "Does the application also require positioning?":
      "Benötigt die Anwendung zusätzlich eine Positionierung?",
    "Is long battery life / low power consumption a major requirement?":
      "Sind lange Batterielaufzeit bzw. geringer Stromverbrauch wichtige Anforderungen?",
    "Which cellular technology best fits the project?":
      "Welche Mobilfunktechnologie passt am besten zum Projekt?",
    "Where will the product be deployed?":
      "In welcher Region soll das Produkt eingesetzt werden?",
    "Should the wireless solution be standalone / AT-command based or host-based?":
      "Soll die Funklösung eigenständig / AT-Befehl-basiert oder host-basiert arbeiten?",
    "How should the Bluetooth module be used in the application?":
      "Wie soll das Bluetooth-Modul in der Anwendung eingesetzt werden?",
    "Which module antenna approach do you prefer?":
      "Welche Antennenvariante des Moduls bevorzugen Sie?",
    "Which radio system must the antenna support?":
      "Welches Funksystem muss die Antenne unterstützen?",
    "Which GNSS band capability do you need?":
      "Welche GNSS-Bandunterstützung benötigen Sie?",
    "Which Wi-Fi / Bluetooth frequency coverage do you need?":
      "Welche Frequenzabdeckung für Wi-Fi / Bluetooth benötigen Sie?",
    "Do you need an active or passive GNSS antenna?":
      "Benötigen Sie eine aktive oder passive GNSS-Antenne?",
    "Which Wi-Fi generation is required?":
      "Welche Wi-Fi-Generation wird benötigt?",
    "Which Wi-Fi generations are acceptable? You can select more than one.":
      "Welche Wi-Fi-Generationen sind geeignet? Sie können mehrere auswählen.",
    "What positioning accuracy is required?":
      "Welche Positionierungsgenauigkeit wird benötigt?",
    "What positioning performance does your application need?":
      "Welche Positionierungsgenauigkeit benötigt Ihre Anwendung?",
    "What minimum Bluetooth LE version does your application require?":
      "Welche minimale Bluetooth-LE-Version benötigt Ihre Anwendung?",
    "Should Bluetooth LE also be included in the wireless solution?":
      "Soll Bluetooth LE ebenfalls in der Funklösung enthalten sein?",
    "Which GNSS frequency-band capability does your application need?":
      "Welche GNSS-Frequenzband-Fähigkeit benötigt Ihre Anwendung?",
    "Which host interface does your system support?":
      "Welche Host-Schnittstelle unterstützt Ihr System?",
    "Which external antenna connection do you prefer?":
      "Welchen externen Antennenanschluss bevorzugen Sie?",
    "How many antenna connections do you need?":
      "Wie viele Antennenanschlüsse benötigen Sie?",
    "Do you have a preferred module form factor?":
      "Bevorzugen Sie eine bestimmte Modulbauform?",
    "Do you want to set a maximum module footprint?":
      "Möchten Sie eine maximale Modulfläche festlegen?",
    "What would you like to do next?":
      "Was möchten Sie als Nächstes tun?",
    "Which result should the SE FAE review?":
      "Welches Ergebnis soll ein SE FAE prüfen?",
    "Which result should SE follow up on?":
      "Zu welchem Ergebnis soll SE nachfassen?",
    "What should the FAE focus on?":
      "Worauf soll sich der FAE konzentrieren?",
    "What quantity should SE use for the commercial check?":
      "Welche Menge soll SE für die kaufmännische Prüfung verwenden?",
    "When do you expect to need the parts?":
      "Wann benötigen Sie voraussichtlich die Teile?",
    "Would you like SE technical or commercial support for this project?":
      "Möchten Sie für dieses Projekt technische oder kaufmännische Unterstützung von SE?",
    "Is this a new design, or are you replacing an existing component?":
      "Handelt es sich um ein neues Design oder ersetzen Sie eine bestehende Komponente?",
    "Which existing component or part number are you replacing?":
      "Welche bestehende Komponente bzw. Teilenummer soll ersetzt werden?",
    "What annual production volume is planned?":
      "Welche jährliche Produktionsmenge ist geplant?",
    "What is the current project phase / timeline?":
      "In welcher Projektphase befindet sich das Projekt?",
    "Are any project partners involved? You can select more than one.":
      "Sind Projektpartner beteiligt? Sie können mehrere auswählen.",
  };

  let text = exact[question.text] ?? question.text;

  const categoryMatch = question.text.match(/^Which (.+) product type is closest to your requirement\?$/);
  if (categoryMatch) {
    text = "Welcher Produkttyp passt am besten zu Ihrer Anforderung?";
  }

  const tieTranslations: Array<[RegExp, string]> = [
    [/^To narrow these Wi-Fi candidates down: which host interface does your system require\?$/, "Welche Host-Schnittstelle benötigt Ihr System, um die Wi-Fi-Kandidaten einzugrenzen?"],
    [/^You mentioned small size\. Do you have a maximum module footprint\?$/, "Sie haben eine kleine Baugröße genannt. Gibt es eine maximale Modulfläche?"],
    [/^Which external antenna connection is preferred\?$/, "Welcher externe Antennenanschluss wird bevorzugt?"],
    [/^How many external antenna connections does the design require\?$/, "Wie viele externe Antennenanschlüsse benötigt das Design?"],
    [/^Is Bluetooth also required, and if so is there a minimum version\?$/, "Wird zusätzlich Bluetooth benötigt? Falls ja, gibt es eine Mindestversion?"],
    [/^Which mechanical form factor is preferred for the cellular solution\?$/, "Welche mechanische Bauform wird für die Mobilfunklösung bevorzugt?"],
    [/^Is dual-band GNSS \(L1 \+ L5\) required, or is L1 sufficient\?$/, "Wird Dual-Band-GNSS (L1 + L5) benötigt oder reicht L1 aus?"],
    [/^For this RTK \/ centimeter-level application, do you require dual-band GNSS \(L1 \+ L5\), or is L1 sufficient\?$/, "Benötigen Sie für diese RTK-/Zentimeter-Anwendung Dual-Band-GNSS (L1 + L5) oder reicht L1 aus?"],
    [/^What maximum module footprint would you like to target\?$/, "Welche maximale Modulfläche soll eingehalten werden?"],
    [/^Which mechanical form factor is preferred for the GNSS receiver\?$/, "Welche mechanische Bauform wird für den GNSS-Empfänger bevorzugt?"],
    [/^Do you have a minimum Bluetooth LE version requirement\?$/, "Gibt es eine Mindestanforderung an die Bluetooth-LE-Version?"],
    [/^For this high-precision GNSS application, which frequency-band capability is required\?$/, "Welche Frequenzband-Fähigkeit wird für diese hochpräzise GNSS-Anwendung benötigt?"],
  ];
  for (const [pattern, translated] of tieTranslations) {
    if (pattern.test(question.text)) {
      text = translated;
      break;
    }
  }

  return {
    ...question,
    text,
    options: localizeOptions(question.options, language),
  };
}

const ENGINEERING_LABELS_DE: Record<string, string> = {
  frequency_hz: "Frequenz",
  supply_voltage_v: "Versorgungsspannung",
  rated_voltage_v: "Nennspannung",
  rated_current_a: "Nennstrom",
  current_rating_a: "Strombelastbarkeit",
  interface: "Schnittstelle",
  mounting: "Montage",
  package: "Bauform / Gehäuse",
  temperature_min_c: "Minimale Betriebstemperatur",
  temperature_max_c: "Maximale Betriebstemperatur",
  load_capacitance_pf: "Lastkapazität",
  frequency_tolerance_ppm: "Frequenztoleranz",
  frequency_stability_ppm: "Frequenzstabilität",
  esr_ohm: "ESR",
  drive_level_uw: "Ansteuerleistung",
  oscillator_type: "Oszillatortyp",
  output_type: "Taktausgang",
  phase_jitter_ps: "Phasenjitter",
  timing_function: "Timing-Funktion",
  choke_type: "Drosseltyp",
  inductance_uh: "Induktivität",
  dc_resistance_ohm: "Gleichstromwiderstand",
  impedance_ohm: "Impedanz",
  test_frequency_hz: "Prüffrequenz",
  relay_type: "Relaistyp",
  contact_form: "Kontaktform",
  coil_voltage_v: "Spulenspannung",
  contact_current_a: "Kontaktstrom",
  contact_voltage_v: "Kontaktspannung",
  switch_type: "Schaltertyp",
  poles: "Pole",
  positions: "Positionen / Kontakte",
  connector_type: "Steckverbindertyp",
  pitch_mm: "Raster",
  display_size_in: "Displaygröße",
  resolution: "Auflösung",
  touch: "Touch",
  storage_capacity_gb: "Speicherkapazität",
  storage_interface: "Speicherschnittstelle",
  cpu_arch: "CPU-Architektur",
  ram_gb: "Arbeitsspeicher",
  onboard_storage_gb: "Onboard-Speicher",
  ethernet_speed_mbps: "Ethernet-Geschwindigkeit",
  pressure_range_kpa: "Druckbereich",
  accuracy_pct: "Genauigkeit",
  force_range_n: "Kraftbereich",
  airflow_range_lpm: "Luftstrombereich",
  humidity_max_pct: "Feuchtebereich",
  measurement_temp_min_c: "Messbereich Minimum",
  measurement_temp_max_c: "Messbereich Maximum",
  temperature_accuracy_c: "Temperaturgenauigkeit",
  axes: "Achsen",
  accel_range_g: "Beschleunigungsbereich",
  gyro_range_dps: "Gyroskopbereich",
  gas_type: "Gas / Luftqualitätsziel",
  audio_interface: "Audio-Schnittstelle",
  sample_rate_khz: "Abtastrate",
  vibration_type: "Haptik-Aktuatortyp",
};

function humanizeEngineeringKey(key: string) {
  const suffixes = [
    "_frequency_hz", "_voltage_v", "_current_a", "_resistance_ohm", "_impedance_ohm",
    "_capacitance_pf", "_tolerance_ppm", "_stability_ppm", "_jitter_ps", "_level_uw",
    "_capacity_gb", "_storage_gb", "_speed_mbps", "_range_kpa", "_range_lpm",
    "_accuracy_c", "_accuracy_pct", "_range_dps", "_range_g", "_mm", "_hz", "_gb", "_a", "_v", "_c"
  ];
  let cleaned = key;
  for (const suffix of suffixes) {
    if (cleaned.endsWith(suffix) && cleaned.length > suffix.length) {
      cleaned = cleaned.slice(0, -suffix.length) + suffix.replace(/^_/, " ");
      break;
    }
  }
  const words = cleaned.split("_").filter(Boolean).map((word) => {
    const upper: Record<string, string> = {
      dc: "DC", esr: "ESR", cpu: "CPU", ram: "RAM", rf: "RF", emi: "EMI",
      emc: "EMC", rtc: "RTC", gnss: "GNSS", usb: "USB", pcie: "PCIe",
    };
    return upper[word] ?? word;
  });
  const value = words.join(" ");
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : key;
}

function engineeringRequirementLabel(key: string, language: Language) {
  if (language === "de" && ENGINEERING_LABELS_DE[key]) return ENGINEERING_LABELS_DE[key];
  return humanizeEngineeringKey(key);
}

function requirementLabel(key: string, language: Language) {
  if (key.startsWith("engineering:")) {
    return engineeringRequirementLabel(key.slice("engineering:".length), language);
  }
  return language === "de" ? (LABELS_DE[key] ?? LABELS[key] ?? key) : (LABELS[key] ?? key);
}

const ENGINEERING_VALUE_LABELS: Record<string, string> = {
  i2c: "I²C", spi: "SPI", uart: "UART", usb: "USB", pcie: "PCIe", sdio: "SDIO",
  can: "CAN", ethernet: "Ethernet", sata: "SATA", nvme: "NVMe", mipi: "MIPI", lvds: "LVDS", rgb: "RGB",
  smd: "SMD / SMT", tht: "Through-hole / THT",
  xo: "XO", tcxo: "TCXO", vcxo: "VCXO", ocxo: "OCXO", lvcmos: "LVCMOS / CMOS", hcsl: "HCSL",
  clipped_sine: "Clipped sine", sine: "Sine wave",
  common_mode: "Common-mode", power: "Power", suppression: "EMI suppression", saturation: "Saturation",
  network_sync: "Network synchronizer", jitter_cleaner: "Jitter cleaner", clock_buffer: "Clock buffer", clock_generator: "Clock generator", rtc: "RTC",
  solid_state: "Solid-state", reed: "Reed", latching: "Latching", signal: "Signal",
  spst: "SPST", spdt: "SPDT", dpst: "DPST", dpdt: "DPDT", "1a": "1 Form A", "1c": "1 Form C", "2c": "2 Form C",
  tactile: "Tactile", toggle: "Toggle", slide: "Slide", dip: "DIP", rotary: "Rotary", rocker: "Rocker", pushbutton: "Pushbutton",
  board_to_board: "Board-to-board", wire_to_board: "Wire-to-board", fpc: "FPC / FFC", rj45: "RJ45", terminal: "Terminal block", circular: "Circular",
  msata: "mSATA", emmc: "eMMC", sd: "SD / microSD", arm: "ARM", x86: "x86 / x86-64", riscv: "RISC-V",
  imu: "IMU", accelerometer: "Accelerometer", gyroscope: "Gyroscope", magnetometer: "Magnetometer", hall: "Hall sensor",
  co2: "CO₂", co: "CO", voc: "VOC", no2: "NO₂", o2: "O₂", air_quality: "Air quality / multi-gas",
  i2s: "I²S", tdm: "TDM", pcm: "PCM", analog: "Analog", digital: "Digital",
  erm: "ERM", lra: "LRA", piezo: "Piezo", feedthrough: "Feed-through", lc_pi: "LC / pi", line: "Mains / line",
};

function formatEngineeringRequirementValue(field: string, value: unknown) {
  if (value === true || String(value).toLowerCase() === "true") return "Yes";
  if (value === false || String(value).toLowerCase() === "false") return "No";

  const canonical = String(value ?? "");
  if (ENGINEERING_VALUE_LABELS[canonical.toLowerCase()]) {
    return ENGINEERING_VALUE_LABELS[canonical.toLowerCase()];
  }

  const number = Number(canonical);
  if (!Number.isFinite(number)) return canonical.replaceAll("_", " ");

  const compact = (v: number) => Number.isInteger(v) ? String(v) : Number(v.toPrecision(7)).toString();
  if (["frequency_hz", "test_frequency_hz", "cutoff_frequency_hz"].includes(field)) {
    if (Math.abs(number) >= 1e9) return `${compact(number / 1e9)} GHz`;
    if (Math.abs(number) >= 1e6) return `${compact(number / 1e6)} MHz`;
    if (Math.abs(number) >= 1e3) return `${compact(number / 1e3)} kHz`;
    return `${compact(number)} Hz`;
  }

  const units: Record<string, string> = {
    supply_voltage_v: "V", rated_voltage_v: "V", coil_voltage_v: "V", contact_voltage_v: "V",
    rated_current_a: "A", current_rating_a: "A", contact_current_a: "A",
    load_capacitance_pf: "pF", frequency_tolerance_ppm: "ppm", frequency_stability_ppm: "ppm",
    esr_ohm: "Ω", dc_resistance_ohm: "Ω", impedance_ohm: "Ω", drive_level_uw: "µW", phase_jitter_ps: "ps",
    inductance_uh: "µH", attenuation_db: "dB", rated_power_w: "W", pitch_mm: "mm", display_size_in: "in",
    storage_capacity_gb: "GB", onboard_storage_gb: "GB", ram_gb: "GB", ethernet_speed_mbps: "Mbit/s",
    pressure_range_kpa: "kPa", accuracy_pct: "%", force_range_n: "N", airflow_range_lpm: "L/min", humidity_max_pct: "%RH",
    temperature_min_c: "°C", temperature_max_c: "°C", measurement_temp_min_c: "°C", measurement_temp_max_c: "°C", temperature_accuracy_c: "°C",
    accel_range_g: "g", gyro_range_dps: "°/s", sample_rate_khz: "kHz",
  };
  return `${compact(number)}${units[field] ? ` ${units[field]}` : ""}`;
}

function localizeValue(value: unknown, language: Language) {
  if (Array.isArray(value)) {
    return value.map((v) => language === "de" ? (OPTION_DE[String(v)] ?? String(v)) : String(v)).join(" + ");
  }
  if (value === true) return language === "de" ? "Ja" : "Yes";
  if (value === false) return language === "de" ? "Nein" : "No";
  const raw = String(value ?? "");
  return language === "de" ? (OPTION_DE[raw] ?? raw) : raw;
}

function localizeReason(reason: string, language: Language) {
  if (language === "en") return reason;
  return reason
    .replace(/^Product type:/, "Produkttyp:")
    .replace(/^Technology:/, "Technologie:")
    .replace(/^Interface:/, "Schnittstelle:")
    .replace(/^Region:/, "Region:")
    .replace(/^Architecture:/, "Architektur:")
    .replace(/^Antenna:/, "Antenne:")
    .replace(/^Antenna application:/, "Antennenanwendung:")
    .replace(/^Antenna band:/, "Antennenband:")
    .replace(/^Antenna type:/, "Antennentyp:")
    .replace(/^Cellular class:/, "Mobilfunkklasse:")
    .replace(/^GNSS precision:/, "GNSS-Genauigkeit:")
    .replace(/^Not verified:/, "Noch zu bestätigen:");
}


const LABELS: Record<string, string> = {
  productDomain: "Product area",
  catalogCategory: "Product type",
  genericInterface: "Interface",
  application: "Application",
  supportRequested: "SE support",
  supportGoal: "Next step",
  supportProduct: "Product for follow-up",
  supportTopic: "FAE focus",
  designSituation: "Project situation",
  existingComponent: "Existing component",
  specialRequirements: "Special requirements",
  targetVolume: "Annual volume",
  projectTimeline: "Project phase",
  projectPartners: "Project partners",
  technologies: "Technology",
  positioning: "Positioning",
  lowPower: "Low power",
  cellularClass: "Cellular class",
  region: "Region",
  architecture: "Architecture",
  antenna: "Antenna",
  wifiGeneration: "Wi-Fi generation",
  gnssPrecision: "GNSS precision",
  hostInterface: "Host interface",
  antennaConnector: "Antenna connector",
  antennaCount: "Antenna connections",
  antennaApplication: "Antenna application",
  antennaGnssBand: "GNSS antenna band",
  antennaWifiBand: "Wi-Fi / Bluetooth band",
  antennaBand: "Antenna band",
  antennaActive: "GNSS antenna type",
  bluetoothRequirement: "Bluetooth requirement",
  maxFootprint: "Maximum footprint",
  formFactor: "Form factor",
  gnssDualBand: "GNSS bands",
};

const htmlEscape = (value: unknown) =>
  String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const valueText = (value: unknown) => {
  if (Array.isArray(value)) return value.join(" + ");
  if (value === true) return "Yes";
  if (value === false) return "No";
  return String(value ?? "");
};




const DOMAIN_OPTIONS: Option[] = [
  { label: "Connectivity / Wireless", value: "connectivity" },
  { label: "GNSS / Positioning", value: "positioning" },
  { label: "Sensors", value: "sensors" },
  { label: "Antennas / RF", value: "antenna" },
  { label: "Displays / HMI", value: "display" },
  { label: "Storage", value: "storage" },
  { label: "Timing", value: "timing" },
  { label: "Embedded Computing", value: "computing" },
  { label: "Components / EMC", value: "components" },
  { label: "Audio / Haptics", value: "audio_haptics" },
];

const DOMAIN_CATEGORY_OPTIONS: Record<string, Option[]> = {
  sensors: [
    { label: "Motion Sensors", value: "Motion Sensors" },
    { label: "Pressure Sensors", value: "Pressure Sensors" },
    { label: "Force Sensors", value: "Force Sensors" },
    { label: "Airflow Sensors", value: "Airflow Sensors" },
    { label: "Humidity Sensors", value: "Humidity Sensors" },
    { label: "Temperature Sensors", value: "Temperature Sensors" },
    { label: "Hall / Magnetic Sensors", value: "Hall / Magnetic Sensors" },
    { label: "Gas Sensors", value: "Gas Sensors" },
  ],
  antenna: [
    { label: "External Antennas", value: "External Antennas" },
    { label: "SMD Antennas", value: "SMD Antennas" },
    { label: "Embedded Antennas", value: "Embedded Antennas" },
    { label: "Other RF Components", value: "Other RF Components" },
  ],
  display: [
    { label: "TFT Displays", value: "TFT Displays" },
    { label: "OLED Displays", value: "OLED Displays" },
    { label: "Character Displays", value: "Character Displays" },
    { label: "Graphic Displays", value: "Graphic Displays" },
    { label: "Smart Displays", value: "Smart Displays" },
    { label: "Display Driver IC", value: "Display Driver IC" },
  ],
  storage: [
    { label: "Flash Storage", value: "Flash Storage" },
    { label: "Embedded Peripherals", value: "Embedded Peripherals" },
  ],
  timing: [
    { label: "Real-Time Clocks (RTCs)", value: "RTCs" },
    { label: "Oscillators", value: "Oscillators" },
    { label: "Timing IC", value: "Timing IC" },
    { label: "Crystals", value: "Crystals" },
  ],
  computing: [
    { label: "Computer on Modules", value: "Computer on Modules" },
    { label: "Single Board Computer", value: "Single Board Computer" },
    { label: "Embedded Peripherals", value: "Embedded Peripherals" },
  ],
  components: [
    { label: "Capacitors", value: "Capacitors" },
    { label: "Relays", value: "Relays" },
    { label: "Contactors", value: "Contactors" },
    { label: "Switches", value: "Switches" },
    { label: "Connectors", value: "Connectors" },
    { label: "Chokes", value: "Chokes" },
    { label: "EMI / EMC Filters", value: "EMI / EMC Filters" },
    { label: "EMI Accessories", value: "EMI Accessories" },
  ],
  audio_haptics: [
    { label: "Vibration / Haptics", value: "Vibration" },
    { label: "Audio Codecs", value: "Audio Codecs" },
  ],
};

function defaultTechnologiesForDomain(domain?: string): string[] {
  if (domain === "positioning") return ["gnss"];
  if (domain === "sensors") return ["sensor"];
  if (domain === "storage") return ["storage"];
  if (domain === "display") return ["display"];
  if (domain === "timing") return ["timing"];
  if (domain === "antenna") return ["antenna"];
  return [];
}

function domainDisplayName(domain?: string) {
  return DOMAIN_OPTIONS.find((option) => option.value === domain)?.label ?? domain ?? "";
}

function domainSpecialRequirementOptions(domain?: string): Option[] {
  const common: Option[] = [
    { label: "Small size", value: "Small size" },
    { label: "Extended temperature range", value: "Extended temperature range" },
  ];

  if (domain !== "antenna" && domain !== "components") {
    common.splice(1, 0, { label: "Battery powered / Low power", value: "Battery powered / Low power" });
  }

  common.push({ label: "No special requirements", value: "No special requirements" });
  return common;
}

function recommendationConfidenceLabel(match: Match, language: Language) {
  if (match.recommendation_confidence === "verified_fit") {
    return tr(language, "Verified", "Verifiziert");
  }
  if (match.recommendation_confidence === "fae_verification_required") {
    return tr(language, "Needs verification", "Prüfung erforderlich");
  }
  return tr(language, "Catalog-supported", "Katalog-gestützt");
}

function recommendationConfidenceClass(match: Match) {
  if (match.recommendation_confidence === "verified_fit") return "fitVerified";
  if (match.recommendation_confidence === "fae_verification_required") return "fitReview";
  return "fitProvisional";
}

function verificationIssueText(match: Match, language: Language) {
  if (!match.verification_issues.length) return "";
  const issues = match.verification_issues.join(", ");
  return tr(language, `Verification needed: ${issues}`, `Zu prüfen: ${issues}`);
}

function customerEvidenceBadge(match: Match, language: Language): string | null {
  if (match.evidence_summary.verified > 0) return tr(language, "Based on manufacturer documentation", "Basierend auf Herstellerdokumentation");
  if (match.evidence_summary.inferred > 0) return tr(language, "Based on SE product data", "Basierend auf SE-Produktdaten");
  return null;
}

function customerCriterionLabel(item: MatchCriterionEvidence, language: Language) {
  if (item.status === "verified") return tr(language, "Confirmed in technical documentation", "In technischer Dokumentation bestätigt");
  if (item.status === "inferred") return tr(language, "Available in SE product data", "In SE-Produktdaten verfügbar");
  if (item.status === "conflicting") return tr(language, "Technical review recommended", "Technische Prüfung empfohlen");
  return tr(language, "Specification confirmation recommended", "Spezifikation sollte bestätigt werden");
}

function evidenceStatusLabel(status: MatchCriterionEvidence["status"]) {
  if (status === "verified") return "Verified";
  if (status === "inferred") return "Inferred";
  if (status === "conflicting") return "Conflicting";
  return "Not verified";
}

function evidenceStatusIcon(status: MatchCriterionEvidence["status"]) {
  if (status === "verified") return "✓";
  if (status === "inferred") return "~";
  if (status === "conflicting") return "!";
  return "?";
}

function evidenceSourceLabel(item: MatchCriterionEvidence) {
  const rawTitle = item.source_title?.trim() || "";
  const title = rawTitle.replace(/\s+—\s+page\s+\d+\s*$/i, "");
  const fallback =
    item.source_type === "catalog_description"
      ? "SE catalog"
      : item.source_type
        ? item.source_type.replace(/_/g, " ")
        : "";

  const base = title || fallback;
  if (!base) return "";

  return item.page_number ? `${base} · p. ${item.page_number}` : base;
}


function parseCapacitanceUf(text: string): number | null {
  const m = text.match(/(\d+(?:[.,]\d+)?)\s*(pF|nF|uF|µF|μF|mF|F)\b/i);
  if (!m) return null;
  const value = Number(m[1].replace(",", "."));
  const unit = m[2].toLowerCase();
  const factor =
    unit === "pf" ? 1e-6 :
    unit === "nf" ? 1e-3 :
    unit === "mf" ? 1e3 :
    unit === "f" ? 1e6 : 1;
  return value * factor;
}

function formatCapacitanceUf(value: number): string {
  const clean = (n: number) => Number(n.toPrecision(6)).toString();
  if (value >= 1e6) return `${clean(value / 1e6)} F`;
  if (value >= 1000) return `${clean(value / 1000)} mF`;
  if (value >= 1) return `${clean(value)} µF`;
  if (value >= 0.001) return `${clean(value * 1000)} nF`;
  return `${clean(value * 1e6)} pF`;
}

function parseSimpleNumber(text: string): number | null {
  const m = text.match(/-?\d+(?:[.,]\d+)?/);
  return m ? Number(m[0].replace(",", ".")) : null;
}

function parseEsrOhm(text: string): number | null {
  const m = text.match(/(\d+(?:[.,]\d+)?)\s*(mohm|mΩ|ohm|Ω)/i);
  if (!m) return null;
  const v = Number(m[1].replace(",", "."));
  return /^m/i.test(m[2]) ? v / 1000 : v;
}

function parseCurrentA(text: string): number | null {
  const m = text.match(/(\d+(?:[.,]\d+)?)\s*(mA|A)\b/i);
  if (!m) return null;
  const v = Number(m[1].replace(",", "."));
  return m[2].toLowerCase() === "ma" ? v / 1000 : v;
}

function capacitorTechnologyFromText(text: string): string | undefined {
  const t = text.toLowerCase();
  if (/super\s*cap|supercapacitor|ultracap|edlc/.test(t)) return "Supercapacitor";
  if (/tantal/.test(t) && /polymer/.test(t)) return "Tantalum polymer";
  if (/tantal/.test(t)) return "Tantalum";
  if (/ceramic|mlcc|keramik|\bx7r\b|\bx5r\b|\bc0g\b|\bnp0\b|\by5v\b/.test(t)) return "Ceramic";
  if (/film|polypropylene|polyester|folie/.test(t)) return "Film";
  if (/alumin(?:um|ium).*(electrolytic|elektrolyt)|\belko\b/.test(t)) return "Aluminum electrolytic";
  if (/polymer/.test(t)) return "Polymer";
  return undefined;
}

function inferFromText(text: string): Partial<Requirements> {
  const t = text.toLowerCase();
  const out: Partial<Requirements> = {};

  if (/asset|tracker|tracking|pallet|container|logistic|nachverfolgung|objektverfolgung/.test(t)) out.application = "asset tracking";
  else if (/gateway|industrial iot|factory|industrie[- ]?gateway|industrieautomation|fabrikautomation/.test(t)) out.application = "industrial IoT";
  else if (/agricultur|agri[- ]?(?:tech|culture)?|argecltural|precision farming|precision agriculture|\bfarming\b|\bfarm\b|tractor guidance|landwirtschaft|präzisionslandwirtschaft|praezisionslandwirtschaft/.test(t)) out.application = "agriculture / precision farming";
  else if (/robot|autonomous|agv|amr|drone|robotik|autonom/.test(t)) out.application = "robotics / autonomous";
  else if (/medical|wearable|health|medizin|gesundheit/.test(t)) out.application = "medical / wearable";
  else if (/storage|ssd|memory/.test(t)) out.application = "industrial storage";
  else if (/display|hmi/.test(t)) out.application = "display / HMI";
  else if (/meter|metering/.test(t)) out.application = "metering";

  // Product-domain fallback router.
  if (/pressure\s+(sensor|transducer)|barometric|drucksensor|druckaufnehmer/.test(t)) {
    out.productDomain = "sensors";
    out.catalogCategory = "Pressure Sensors";
  } else if (/temperature\s+sensor|thermistor|temperatursensor|temperaturmessung/.test(t)) {
    out.productDomain = "sensors";
    out.catalogCategory = "Temperature Sensors";
  } else if (/humidity\s+sensor|feuchtigkeitssensor|luftfeuchtigkeit/.test(t)) {
    out.productDomain = "sensors";
    out.catalogCategory = "Humidity Sensors";
  } else if (/motion\s+sensor|\bimu\b|accelerometer|gyroscope|ahrs|bewegungssensor|beschleunigungssensor|gyroskop/.test(t)) {
    out.productDomain = "sensors";
    out.catalogCategory = "Motion Sensors";
  } else if (/force\s+sensor|load\s+cell|strain\s+(sensor|gauge)/.test(t)) {
    out.productDomain = "sensors";
    out.catalogCategory = "Force Sensors";
  } else if (/air\s*flow\s+sensor|airflow\s+sensor|mass\s+flow/.test(t)) {
    out.productDomain = "sensors";
    out.catalogCategory = "Airflow Sensors";
  } else if (/hall\s+(effect\s+)?sensor|magnetic\s+sensor|magnetometer/.test(t)) {
    out.productDomain = "sensors";
    out.catalogCategory = "Hall / Magnetic Sensors";
  } else if (/gas\s+sensor|co2\s+sensor|air quality sensor/.test(t)) {
    out.productDomain = "sensors";
    out.catalogCategory = "Gas Sensors";
  } else if (/\bcapacitors?\b|\bkondensator(en)?\b/.test(t)) {
    out.productDomain = "components";
    out.catalogCategory = "Capacitors";
  } else if (/\brelays?\b|\brelais\b/.test(t)) {
    out.productDomain = "components";
    out.catalogCategory = "Relays";
  } else if (/\bcontactors?\b|\bschütz(e)?\b|\bschuetz(e)?\b/.test(t)) {
    out.productDomain = "components";
    out.catalogCategory = "Contactors";
  } else if (/\bconnectors?\b|\bsteckverbinder\b/.test(t)) {
    out.productDomain = "components";
    out.catalogCategory = "Connectors";
  } else if (/\bchokes?\b|\bdrossel(n)?\b/.test(t)) {
    out.productDomain = "components";
    out.catalogCategory = "Chokes";
  } else if (/\b(emi|emc|emv)\b.*\bfilter\b/.test(t)) {
    out.productDomain = "components";
    out.catalogCategory = "EMI / EMC Filters";
  } else if (/\bsensor\b|\bsensing\b|\bsensorik\b|\bsensoren?\b/.test(t)) {
    out.productDomain = "sensors";
  } else if (/\btft\b/.test(t)) {
    out.productDomain = "display";
    out.catalogCategory = "TFT Displays";
  } else if (/\boled\b/.test(t)) {
    out.productDomain = "display";
    out.catalogCategory = "OLED Displays";
  } else if (/\bdisplay\b|\bhmi\b|\bscreen\b|\banzeige\b|\bbildschirm\b/.test(t)) {
    out.productDomain = "display";
  } else if (/computer[- ]on[- ]modules?|\bsmarc\b|com\s*express|\bqseven\b|rechnermodul/.test(t)) {
    out.productDomain = "computing";
    out.catalogCategory = "Computer on Modules";
  } else if (/single[- ]board\s+computers?|\bsbc\b|pico[- ]?itx|einplatinenrechner/.test(t)) {
    out.productDomain = "computing";
    out.catalogCategory = "Single Board Computer";
  } else if (/embedded\s+peripherals?|embedded[- ]?peripherie/.test(t)) {
    out.productDomain = "computing";
    out.catalogCategory = "Embedded Peripherals";
  } else if (/\bssd\b|\bnvme\b|flash storage|msata|cfast|satadom/.test(t)) {
    out.productDomain = "storage";
    out.catalogCategory = "Flash Storage";
  } else if (/\bstorage\b|\bmemory\b|\bspeicher\b|\bdatenspeicher\b/.test(t)) {
    out.productDomain = "storage";
  } else if (/\brtc\b|real[- ]time clock/.test(t)) {
    out.productDomain = "timing";
    out.catalogCategory = "RTCs";
  } else if (/oscillator|tcxo|ocxo|vcxo/.test(t)) {
    out.productDomain = "timing";
    out.catalogCategory = "Oscillators";
  } else if (/quartz crystal|\bcrystal\b/.test(t)) {
    out.productDomain = "timing";
    out.catalogCategory = "Crystals";
  } else if (/\btiming\b|\bclock\b|\btakt(ung)?\b|\bzeitgeber\b/.test(t)) {
    out.productDomain = "timing";
  } else if (/\bcomputing\b|\bembedded computer\b|\bcomputer\b|\brechner\b/.test(t)) {
    out.productDomain = "computing";
  } else if (/\bcomponents?\b|\bpassive components?\b|\bbauteil(e)?\b|\bkomponent(e|en)\b|\bemc\b|\bemi\b|\bemv\b/.test(t)) {
    out.productDomain = "components";
  } else if (/external antenna|smd antenna|chip antenna|embedded antenna|extern(e|en|er|es)? antenne|smd-?antenne|chip-?antenne|eingebettet(e|en|er|es)? antenne|leiterplattenantenne/.test(t)) {
    out.productDomain = "antenna";
    if (/external antenna|externe antenne/.test(t)) out.catalogCategory = "External Antennas";
    else if (/smd antenna|chip antenna|smd-?antenne|chip-?antenne/.test(t)) out.catalogCategory = "SMD Antennas";
    else if (/embedded antenna|eingebettete antenne|leiterplattenantenne/.test(t)) out.catalogCategory = "Embedded Antennas";
  }


  // Capacitor-specific values can be supplied directly in the first sentence.
  if (out.productDomain === "antenna") {
    const antennaApps: string[] = [];
    if (/\bgnss\b|\bgps\b|\bgalileo\b|\bglonass\b|\bbeidou\b/.test(t)) antennaApps.push("gnss");
    if (/wi-?fi|\bwlan\b|bluetooth|\bble\b/.test(t)) antennaApps.push("wifi_bt");
    if (/\bcellular\b|\blte\b|\b5g\b|\b4g\b|\bgsm\b|\bumts\b|\blte-?m\b|\bnb-?iot\b/.test(t)) antennaApps.push("cellular");
    if (/\blora\b|\bsigfox\b|\bism\b|\bsub[- ]?ghz\b|\b433\s*mhz\b|\b868\s*mhz\b|\b915\s*mhz\b/.test(t)) antennaApps.push("ism");

    const uniqueApps = [...new Set(antennaApps)];
    if (uniqueApps.length >= 2) out.antennaApplication = "multi";
    else if (uniqueApps.length === 1) out.antennaApplication = uniqueApps[0];

    if (out.antennaApplication === "gnss") {
      if (/dual[- ]band|multi[- ]band|\bl2\b|\bl5\b|\bl1\s*[/+]\s*l(?:2|5)\b/.test(t)) out.antennaBand = "gnss_multiband";
      else if (/\bl1\b|1559\s*[-–]\s*1609/.test(t)) out.antennaBand = "gnss_l1";

      if (/\bactive\b[^.;]{0,24}\b(?:gnss\s+)?(?:patch\s+)?antenna\b|\bactive\s+gnss\b/.test(t)) out.antennaActive = "active";
      else if (/\bpassive\b[^.;]{0,24}\b(?:gnss\s+)?(?:patch\s+)?antenna\b|\bpassive\s+gnss\b/.test(t)) out.antennaActive = "passive";
    } else if (out.antennaApplication === "wifi_bt") {
      if (/wi-?fi\s*6e|\b6e\b|\b6\s*ghz\b/.test(t)) out.antennaBand = "wifi_6e";
      else if (/2[.,]4\s*(?:\+|\/|and)\s*5\s*ghz|dual[- ]band\s+wi-?fi/.test(t)) out.antennaBand = "wifi_245";
      else if (/\b2[.,]4\s*ghz\b/.test(t)) out.antennaBand = "wifi_24";
    }
  }

  if (out.catalogCategory === "Capacitors") {
    const c = parseCapacitanceUf(text);
    if (c != null) out.capacitorCapacitance = formatCapacitanceUf(c);

    const vm = text.match(/(\d+(?:[.,]\d+)?)\s*V\b/i);
    if (vm) out.capacitorVoltage = `${Number(vm[1].replace(",", "."))} V`;

    const tol = text.match(/(?:±|\+\/-|\+-)\s*(\d+(?:[.,]\d+)?)\s*%/);
    if (tol) out.capacitorTolerance = `±${Number(tol[1].replace(",", "."))}%`;

    const technology = capacitorTechnologyFromText(text);
    if (technology) out.capacitorTechnology = technology;

    if (/through[- ]?hole|\btht\b|\bradial\b|\baxial\b|\bleaded\b/.test(t)) {
      out.capacitorMounting = "Through-hole";
    } else if (/\bsmd\b|\bsmt\b|surface[- ]?mount/.test(t)) {
      out.capacitorMounting = "SMD";
    }

    const caseMatch = text.match(/\b(0201|0402|0603|0805|1206|1210|1812|2220)\b/i);
    if (caseMatch) out.capacitorCaseSize = caseMatch[1];

    const esr = /(?:\besr\b|equivalent series resistance)/i.test(text) ? parseEsrOhm(text) : null;
    if (esr != null) out.capacitorEsrMax = `≤ ${esr} Ω`;

    if (/ripple/i.test(text)) {
      const ripple = parseCurrentA(text);
      if (ripple != null) out.capacitorRippleMin = `≥ ${ripple} A`;
    }

    const life = text.match(/(?:life(?:time)?|load life|service life|lebensdauer)[^0-9]{0,16}(\d{2,7})\s*(?:h|hours?|stunden)/i);
    if (life) out.capacitorLifetimeMin = `≥ ${life[1]} h`;

    const temp = text.match(/(-?\d{1,3})\s*(?:°\s*C)?\s*(?:to|\.\.\.|…|-)\s*\+?(-?\d{1,3})\s*°\s*C/i);
    if (temp) out.capacitorTemperatureRange = `${temp[1]}…${temp[2]} °C`;

    const energy = text.match(/(?:energy|stored energy|energie)[^0-9]{0,12}(\d+(?:[.,]\d+)?)\s*(mJ|J)\b/i);
    if (energy) {
      let e = Number(energy[1].replace(",", "."));
      if (energy[2].toLowerCase() === "mj") e /= 1000;
      out.capacitorEnergyMin = `≥ ${e} J`;
    }
  }

  if (/\bi2c\b|\bi²c\b/.test(t)) out.genericInterface = "i2c";
  else if (/\bspi\b/.test(t)) out.genericInterface = "spi";
  else if (/\buart\b/.test(t)) out.genericInterface = "uart";
  else if (/\busb\b/.test(t)) out.genericInterface = "usb";
  else if (/\banalog(ue)?\s+(output|interface)|4\s*-\s*20\s*ma|0\s*-\s*10\s*v/.test(t)) out.genericInterface = "analog";
  else if (/\bdigital\s+(output|interface)/.test(t)) out.genericInterface = "digital";

  const technologies: string[] = [];
  if (/\bwifi\b|wi-fi|wlan/.test(t)) technologies.push("wifi");
  if (/bluetooth|\bble\b/.test(t)) technologies.push("bluetooth");
  if (/gnss|\bgps\b|position|rtk/.test(t)) technologies.push("gnss");
  if (/cellular|lte|nb-iot|nb iot|lte-m|lte m|cat 1|cat1|redcap|mobilfunk/.test(t)) technologies.push("cellular");
  if (out.productDomain === "sensors") technologies.push("sensor");
  if (out.productDomain === "storage") technologies.push("storage");
  if (out.productDomain === "display") technologies.push("display");
  if (out.productDomain === "timing") technologies.push("timing");
  if (out.productDomain === "antenna") technologies.push("antenna");

  const wireless = new Set(technologies);

  if (
    out.productDomain === "antenna" &&
    (wireless.has("wifi") || wireless.has("bluetooth") || wireless.has("cellular") || wireless.has("gnss")) &&
    /\bmodule?\b|\bmodul(e)?\b|\bdevice\b|\bgerät\b|\bgeraet\b/.test(t)
  ) {
    out.productDomain = "connectivity";
    out.catalogCategory = undefined;
    const antennaIndex = technologies.indexOf("antenna");
    if (antennaIndex >= 0) technologies.splice(antennaIndex, 1);
  }

  if (!out.productDomain) {
    if (wireless.has("wifi") || wireless.has("bluetooth") || wireless.has("cellular")) {
      out.productDomain = "connectivity";
    } else if (wireless.has("gnss")) {
      out.productDomain = "positioning";
    }
  }

  if (technologies.length) out.technologies = [...new Set(technologies)];

  if (/cat 1bis|cat1bis|cat-1bis/.test(t)) out.cellularClass = "Cat 1bis";
  else if (/lte-m|lte m|nb-iot|nb iot|lpwa/.test(t)) out.cellularClass = "LPWA";
  else if (/cat 4|cat4/.test(t)) out.cellularClass = "Cat 4";
  else if (/redcap/.test(t)) out.cellularClass = "5G RedCap";

  if (/global|worldwide|weltweit/.test(t)) out.region = "Global";
  else if (/america|usa|united states|canada|nordamerika/.test(t)) out.region = "Americas";
  else if (/europe|germany|emea|apac|asia|europa|deutschland|asien/.test(t)) out.region = "EMEA/APAC";

  if (/battery|low power|ultra low power|batterie|akkubetrieb|stromsparend|niedriger stromverbrauch/.test(t)) out.lowPower = true;

  if (/open cpu|open-cpu|zephyr/.test(t)) out.architecture = "open";
  else if (/u-connect|uconnect|at command|at-befehl|at befehl/.test(t)) out.architecture = "uconnect";
  else if (/host based|host-based|host-basiert\w*|hostbasiert\w*/.test(t)) out.architecture = "host";

  if (/integrated antenna|pcb antenna|internal antenna|integriert(e|en|er|es)? antenne|intern(e|en|er|es)? antenne|leiterplattenantenne/.test(t)) out.antenna = "internal";
  else if (/external antenna|antenna pin|extern(e|en|er|es)? antenne|antennenpin/.test(t)) out.antenna = "external";

  const wifiGenerations: string[] = [];
  if (/wifi[- ]*4|wi-fi[- ]*4|wlan[- ]*4|802\.11n/.test(t)) wifiGenerations.push("4");
  if (/wifi[- ]*5|wi-fi[- ]*5|wlan[- ]*5|802\.11ac/.test(t)) wifiGenerations.push("5");
  if (/wifi[- ]*6(?!e)|wi-fi[- ]*6(?!e)|wlan[- ]*6(?!e)|802\.11ax/.test(t)) wifiGenerations.push("6");
  if (/wifi[- ]*6e|wi-fi[- ]*6e|wlan[- ]*6e|6 ghz/.test(t)) wifiGenerations.push("6E");
  if (wifiGenerations.length) out.wifiGeneration = [...new Set(wifiGenerations)];

  if (/centimeter|centimetre|rtk|high precision|zentimeter|hochpräzise|hochpraezise/.test(t)) out.gnssPrecision = "cm";
  else if (/standard gnss|meter level|metre level|metergenau|meterbereich/.test(t)) out.gnssPrecision = "standard";


  if (/\bsdio\b/.test(t) && /\bpcie\b|pci express/.test(t)) out.hostInterface = "SDIO or PCIe";
  else if (/\bsdio\b/.test(t)) out.hostInterface = "SDIO";
  else if (/\bpcie\b|pci express/.test(t)) out.hostInterface = "PCIe";

  if (/\bu\.?fl\b|\bufl\b/.test(t)) out.antennaConnector = "U.FL";
  else if (/antenna[- ]?pin|ant\.?\s*pins?|solder pads?/.test(t)) out.antennaConnector = "Antenna pin / solder pad";

  const btVersion = t.match(/(?:bluetooth(?:\s+le)?|ble|bt(?:\/ble)?)\s*([4-6](?:\.\d+)?)/);
  if (btVersion) out.bluetoothRequirement = `Bluetooth ${btVersion[1]}+`;

  if (/\bmini\s*pcie\b/.test(t)) out.formFactor = "Mini PCIe";
  else if (/\bm\.?2\b/.test(t)) out.formFactor = "M.2";
  else if (/\blga\b/.test(t)) out.formFactor = "LGA";

  if (/\bl1\s*\+\s*l5\b|dual[- ]band gnss/.test(t)) out.gnssDualBand = "L1 + L5 required";

  return out;
}


async function interpretWithBackend(text: string): Promise<Partial<Requirements>> {
  const response = await fetch(`${API}/api/requirements/interpret`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, current: null }),
  });
  if (!response.ok) throw new Error(`Interpret HTTP ${response.status}`);

  const data: RequirementInterpretResponse = await response.json();
  const r = data.requirements;

  return {
    application: r.application ?? undefined,
    productDomain: r.product_domain ?? undefined,
    catalogCategory: r.catalog_category ?? undefined,
    genericInterface: r.generic_interface ?? undefined,
    technologies: r.technologies?.length ? r.technologies : undefined,
    cellularClass: r.cellular_class ?? undefined,
    region: r.region ?? undefined,
    architecture: r.architecture ?? undefined,
    antenna: r.antenna ?? undefined,
    wifiGeneration: r.wifi_generation?.length ? r.wifi_generation : undefined,
    gnssPrecision: r.gnss_precision ?? undefined,
    lowPower: r.low_power ?? undefined,
    hostInterface:
      r.host_interface === "sdio" ? "SDIO" :
      r.host_interface === "pcie" ? "PCIe" :
      r.host_interface === "sdio_pcie" ? "SDIO or PCIe" : undefined,
    antennaConnector:
      r.antenna_connector === "ufl" ? "U.FL" :
      r.antenna_connector === "antenna_pin" ? "Antenna pin / solder pad" : undefined,
    antennaCount: r.antenna_count ? String(r.antenna_count) : undefined,
    antennaApplication: r.antenna_application ?? undefined,
    antennaBand: r.antenna_band ?? undefined,
    antennaActive:
      r.antenna_active === true ? "active" :
      r.antenna_active === false ? "passive" : undefined,
    bluetoothRequirement:
      r.bluetooth_version_min ? `Bluetooth ${r.bluetooth_version_min}+` :
      r.bluetooth_required ? "Bluetooth required, version open" : undefined,
    maxFootprint: r.max_footprint_mm2 ? `≤ ${r.max_footprint_mm2} mm²` : undefined,
    formFactor: r.form_factor ?? undefined,
    gnssDualBand: r.gnss_dual_band ? "L1 + L5 required" : undefined,
    engineering: r.engineering_requirements ?? undefined,
    answeredEngineering: r.answered_engineering_fields ?? undefined,
    capacitorCapacitance:
      r.capacitance_uf != null ? formatCapacitanceUf(r.capacitance_uf) : undefined,
    capacitorVoltage:
      r.capacitor_voltage_v != null ? `${r.capacitor_voltage_v} V` : undefined,
    capacitorTolerance:
      r.capacitor_tolerance_pct != null ? `±${r.capacitor_tolerance_pct}%` :
      r.capacitor_tolerance_open ? "No preference" : undefined,
    capacitorTechnology: r.capacitor_technology ?? undefined,
    capacitorMounting: r.capacitor_mounting ?? undefined,
    capacitorCaseSize: r.capacitor_case_size ?? undefined,
    capacitorEsrMax:
      r.capacitor_esr_max_ohm != null ? `≤ ${r.capacitor_esr_max_ohm} Ω` : undefined,
    capacitorRippleMin:
      r.capacitor_ripple_current_min_a != null ? `≥ ${r.capacitor_ripple_current_min_a} A` : undefined,
    capacitorLifetimeMin:
      r.capacitor_lifetime_min_h != null ? `≥ ${r.capacitor_lifetime_min_h} h` : undefined,
    capacitorTemperatureRange:
      r.capacitor_temperature_min_c != null && r.capacitor_temperature_max_c != null
        ? `${r.capacitor_temperature_min_c}…${r.capacitor_temperature_max_c} °C`
        : undefined,
    capacitorEnergyMin:
      r.capacitor_energy_min_j != null ? `≥ ${r.capacitor_energy_min_j} J` : undefined,
  };
}

function questionFor(req: Requirements): { key: QuestionKey; text: string; options?: Option[] } | null {
  if (!req.initialNeed) {
    return {
      key: "initialNeed",
      text: "I am the SE Product Assistant. How can I help you?<br><span class='botHint'>Briefly describe the application, component, or technical requirement you are looking for.</span>",
    };
  }

  if (!req.productDomain) {
    return {
      key: "productDomain",
      text: "Which product area best matches what you are looking for?",
      options: DOMAIN_OPTIONS,
    };
  }

  const categoryOptions = DOMAIN_CATEGORY_OPTIONS[req.productDomain] ?? [];
  if (categoryOptions.length && !req.catalogCategory) {
    const domainName = domainDisplayName(req.productDomain);
    return {
      key: "catalogCategory",
      text: `Which ${domainName.toLowerCase()} product type is closest to your requirement?`,
      options: categoryOptions,
    };
  }

  if (req.productDomain === "connectivity" && !req.technologies?.some((t) =>
      ["wifi", "bluetooth", "cellular", "gnss"].includes(t)
    )) {
    return {
      key: "technologies",
      text: "Which connectivity / positioning technologies are required? You can select more than one.",
      options: [
        { label: "Cellular", value: ["cellular"] },
        { label: "Bluetooth", value: ["bluetooth"] },
        { label: "Wi-Fi", value: ["wifi"] },
        { label: "GNSS", value: ["gnss"] },
      ],
    };
  }

  if (req.productDomain === "antenna") {
    if (!req.antennaApplication) {
      return {
        key: "antennaApplication",
        text: "Which radio system must the antenna support?",
        options: [
          { label: "GNSS", value: "gnss" },
          { label: "Wi-Fi / Bluetooth", value: "wifi_bt" },
          { label: "Cellular / LTE / 5G", value: "cellular" },
          { label: "ISM / LPWAN (433 / 868 / 915 MHz)", value: "ism" },
          { label: "Multi-radio / combination", value: "multi" },
        ],
      };
    }

    if (req.antennaApplication === "gnss" && !req.antennaBand) {
      return {
        key: "antennaGnssBand",
        text: "Which GNSS band capability do you need?",
        options: [
          { label: "GNSS L1", value: "gnss_l1" },
          { label: "GNSS multi-band (L1 + L2/L5)", value: "gnss_multiband" },
          { label: "No fixed band / not sure", value: "No preference" },
        ],
      };
    }

    if (req.antennaApplication === "wifi_bt" && !req.antennaBand) {
      return {
        key: "antennaWifiBand",
        text: "Which Wi-Fi / Bluetooth frequency coverage do you need?",
        options: [
          { label: "2.4 GHz", value: "wifi_24" },
          { label: "2.4 + 5 GHz", value: "wifi_245" },
          { label: "6 GHz / Wi-Fi 6E capable", value: "wifi_6e" },
          { label: "No fixed band / not sure", value: "No preference" },
        ],
      };
    }

    if (req.antennaApplication === "gnss" && !req.antennaActive) {
      return {
        key: "antennaActive",
        text: "Do you need an active or passive GNSS antenna?",
        options: [
          { label: "Active antenna", value: "active" },
          { label: "Passive antenna", value: "passive" },
          { label: "No preference / not sure", value: "No preference" },
        ],
      };
    }
  }

  if (
    req.productDomain === "sensors" &&
    !req.genericInterface
  ) {
    return {
      key: "genericInterface",
      text: "Do you have a preferred electrical interface or sensor output?",
      options: [
        { label: "I²C", value: "i2c" },
        { label: "SPI", value: "spi" },
        { label: "Analog output", value: "analog" },
        { label: "Digital output", value: "digital" },
        { label: "UART", value: "uart" },
        { label: "No preference / not sure", value: "No preference" },
      ],
    };
  }

  if (req.catalogCategory === "Capacitors") {
    if (!req.capacitorCapacitance) {
      return {
        key: "capacitorCapacitance",
        text: "What capacitance do you need?",
        options: [
          { label: "100 nF", value: "100 nF" },
          { label: "1 µF", value: "1 µF" },
          { label: "10 µF", value: "10 µF" },
          { label: "47 µF", value: "47 µF" },
          { label: "100 µF", value: "100 µF" },
        ],
      };
    }

    if (!req.capacitorVoltage) {
      return {
        key: "capacitorVoltage",
        text: "What minimum voltage rating should the capacitor support?",
        options: [
          { label: "6.3 V", value: "6.3 V" },
          { label: "10 V", value: "10 V" },
          { label: "16 V", value: "16 V" },
          { label: "25 V", value: "25 V" },
          { label: "50 V", value: "50 V" },
          { label: "100 V", value: "100 V" },
        ],
      };
    }

    if (!req.capacitorTechnology) {
      return {
        key: "capacitorTechnology",
        text: "Do you have a preferred capacitor technology?",
        options: [
          { label: "Ceramic / MLCC", value: "Ceramic" },
          { label: "Tantalum", value: "Tantalum" },
          { label: "Film", value: "Film" },
          { label: "Aluminum electrolytic", value: "Aluminum electrolytic" },
          { label: "Polymer", value: "Polymer" },
          { label: "Supercapacitor", value: "Supercapacitor" },
          { label: "No preference", value: "No preference" },
        ],
      };
    }

    if (!req.capacitorMounting) {
      return {
        key: "capacitorMounting",
        text: "What mounting style do you need?",
        options: [
          { label: "SMD / SMT", value: "SMD" },
          { label: "Through-hole", value: "Through-hole" },
          { label: "No preference", value: "No preference" },
        ],
      };
    }

    if (!req.capacitorTolerance) {
      return {
        key: "capacitorTolerance",
        text: "Do you have a capacitance tolerance requirement?",
        options: [
          { label: "±5%", value: "±5%" },
          { label: "±10%", value: "±10%" },
          { label: "±20%", value: "±20%" },
          { label: "No preference", value: "No preference" },
        ],
      };
    }
  }

  const tech = new Set(req.technologies ?? []);

  if (req.productDomain === "connectivity") {
    if (req.application === "asset tracking" && !tech.has("gnss") && !req.positioning) {
      return {
        key: "positioning",
        text: "Does the application also require positioning?",
        options: [
          { label: "Yes, GNSS positioning", value: "yes" },
          { label: "No", value: "no" },
        ],
      };
    }

    if (req.application === "asset tracking" && req.lowPower === undefined) {
      return {
        key: "lowPower",
        text: "Is long battery life / low power consumption a major requirement?",
        options: [
          { label: "Yes", value: true },
          { label: "No", value: false },
        ],
      };
    }

    if (tech.has("cellular") && !req.cellularClass) {
      return {
        key: "cellularClass",
        text: "Which cellular technology best fits the project?",
        options: [
          { label: "LTE-M / NB-IoT", value: "LPWA" },
          { label: "LTE Cat 1bis", value: "Cat 1bis" },
          { label: "LTE Cat 4", value: "Cat 4" },
          { label: "5G RedCap", value: "5G RedCap" },
        ],
      };
    }

    if (tech.has("cellular") && !req.region) {
      return {
        key: "region",
        text: "Where will the product be deployed?",
        options: [
          { label: "Global", value: "Global" },
          { label: "Americas", value: "Americas" },
          { label: "Europe / EMEA / APAC", value: "EMEA/APAC" },
        ],
      };
    }

    if ((tech.has("bluetooth") || tech.has("wifi")) && !req.architecture) {
      return {
        key: "architecture",
        text: tech.has("wifi")
          ? "Should the wireless solution be standalone / AT-command based or host-based?"
          : "How should the Bluetooth module be used in the application?",
        options: [
          { label: "Open CPU", value: "open" },
          { label: "u-connectXpress / AT commands", value: "uconnect" },
          { label: "Host-based", value: "host" },
        ],
      };
    }

    if (tech.has("bluetooth") && !req.bluetoothRequirement) {
      return {
        key: "bluetoothRequirement",
        text: "What minimum Bluetooth LE version does your application require?",
        options: [
          { label: "Version open / not sure", value: "Bluetooth required, version open" },
          { label: "Bluetooth LE 5.0 or newer", value: "Bluetooth 5.0+" },
          { label: "Bluetooth LE 5.1 or newer", value: "Bluetooth 5.1+" },
          { label: "Bluetooth LE 5.2 or newer", value: "Bluetooth 5.2+" },
          { label: "Bluetooth LE 5.3 or newer", value: "Bluetooth 5.3+" },
          { label: "Bluetooth LE 5.4 or newer", value: "Bluetooth 5.4+" },
          { label: "Bluetooth LE 6.0 or newer", value: "Bluetooth 6.0+" },
        ],
      };
    }

    if (tech.has("bluetooth") && !req.antenna) {
      return {
        key: "antenna",
        text: "Which module antenna approach do you prefer?",
        options: [
          { label: "Integrated / PCB antenna", value: "internal" },
          { label: "External antenna / antenna pin", value: "external" },
        ],
      };
    }

    if (tech.has("wifi") && !req.wifiGeneration?.length) {
      return {
        key: "wifiGeneration",
        text: "Which Wi-Fi generations are acceptable? You can select more than one.",
        options: [
          { label: "Wi-Fi 4", value: "4" },
          { label: "Wi-Fi 5", value: "5" },
          { label: "Wi-Fi 6", value: "6" },
          { label: "Wi-Fi 6E", value: "6E" },
        ],
      };
    }

    if (tech.has("gnss") && !req.gnssPrecision) {
      return {
        key: "gnssPrecision",
        text: "What positioning performance does your application need?",
        options: [
          { label: "Standard GNSS / meter-level", value: "standard" },
          { label: "High precision / centimeter-level (RTK)", value: "cm" },
          { label: "No fixed accuracy / not sure", value: "No preference" },
        ],
      };
    }

    if (tech.has("gnss") && !req.gnssDualBand) {
      return {
        key: "gnssDualBand",
        text: "Which GNSS frequency-band capability does your application need?",
        options: [
          { label: "L1 is sufficient", value: "L1 sufficient" },
          { label: "Dual-band L1 + L5 required", value: "L1 + L5 required" },
          { label: "No preference / not sure", value: "No preference" },
        ],
      };
    }
  }

  if (req.productDomain === "positioning" && !req.gnssPrecision) {
    return {
      key: "gnssPrecision",
      text: "What positioning performance does your application need?",
      options: [
        { label: "Standard GNSS / meter-level", value: "standard" },
        { label: "High precision / centimeter-level (RTK)", value: "cm" },
        { label: "No fixed accuracy / not sure", value: "No preference" },
      ],
    };
  }

  if (req.productDomain === "positioning" && !req.gnssDualBand) {
    return {
      key: "gnssDualBand",
      text: "Which GNSS frequency-band capability does your application need?",
      options: [
        { label: "L1 is sufficient", value: "L1 sufficient" },
        { label: "Dual-band L1 + L5 required", value: "L1 + L5 required" },
        { label: "No preference / not sure", value: "No preference" },
      ],
    };
  }

  return null;
}



function commercialQuestionFor(
  req: Requirements,
  currentMatches: Match[]
): { key: QuestionKey; text: string; options?: Option[] } | null {
  if (!req.supportGoal) {
    return {
      key: "supportGoal",
      text: "What would you like to do next?",
      options: [
        { label: "Technical review with an SE FAE", value: "technical" },
        { label: "Price / availability / samples", value: "commercial" },
        { label: "No — the recommendation is enough", value: "none" },
      ],
    };
  }

  if (req.supportGoal === "none") return null;

  if (!req.supportProduct) {
    const topProducts = uniqueSolutionMatches(currentMatches)
      .slice(0, 3)
      .map((match) => ({
        label: match.product.part_number,
        value: match.product.part_number,
      }));

    const options: Option[] = [
      ...topProducts,
      ...(topProducts.length > 1
        ? [{ label: "Compare the top candidates", value: "Compare top candidates" }]
        : []),
    ];

    if (options.length) {
      return {
        key: "supportProduct",
        text:
          req.supportGoal === "technical"
            ? "Which result should the SE FAE review?"
            : "Which result should SE follow up on?",
        options,
      };
    }
  }

  if (req.supportGoal === "technical" && !req.supportTopic) {
    return {
      key: "supportTopic",
      text: "What should the FAE focus on?",
      options: [
        { label: "Validate the recommendation", value: "Validate recommendation" },
        { label: "Compare the top candidates", value: "Compare top candidates" },
        { label: "Hardware / interface integration", value: "Hardware / interface integration" },
        { label: "Antenna / RF", value: "Antenna / RF" },
        { label: "Firmware / software", value: "Firmware / software" },
        { label: "Certification / regulatory", value: "Certification / regulatory" },
      ],
    };
  }

  if (req.supportGoal === "commercial") {
    if (!req.targetVolume) {
      return {
        key: "targetVolume",
        text: "What quantity should SE use for the commercial check?",
        options: [
          { label: "< 1,000 units/year", value: "< 1,000 units/year" },
          { label: "1,000–10,000 units/year", value: "1,000–10,000 units/year" },
          { label: "10,000–100,000 units/year", value: "10,000–100,000 units/year" },
          { label: "> 100,000 units/year", value: "> 100,000 units/year" },
          { label: "Still open", value: "Still open" },
        ],
      };
    }

    if (!req.projectTimeline) {
      return {
        key: "projectTimeline",
        text: "When do you expect to need the parts?",
        options: [
          { label: "Prototype / samples now", value: "Prototype / samples now" },
          { label: "Within 3 months", value: "Within 3 months" },
          { label: "3–6 months", value: "3–6 months" },
          { label: "More than 6 months", value: "More than 6 months" },
          { label: "Still open", value: "Still open" },
        ],
      };
    }
  }

  return null;
}

function isCommercialKey(key: QuestionKey): boolean {
  return [
    "supportRequested",
    "supportGoal",
    "supportProduct",
    "supportTopic",
    "designSituation",
    "existingComponent",
    "targetVolume",
    "projectTimeline",
    "projectPartners",
  ].includes(key);
}

function candidateText(match: Match) {
  return `${match.product.part_number} ${match.product.description}`.toLowerCase();
}

function hasCandidateDifference(matches: Match[], extractor: (m: Match) => string | number | null): boolean {
  const values = new Set(
    matches
      .map(extractor)
      .filter((v): v is string | number => v !== null && v !== undefined && v !== "")
      .map(String)
  );
  return values.size >= 2 || (values.size >= 1 && matches.some((m) => extractor(m) == null));
}

function candidateHostInterface(match: Match): string | null {
  const t = candidateText(match).replace(/\bmini\s*pcie\b/g, " ");
  const sdio = /\bsdio\b/.test(t);
  const pcie = /\bpcie\b|pci express/.test(t);
  if (sdio && pcie) return "SDIO + PCIe";
  if (sdio) return "SDIO";
  if (pcie) return "PCIe";
  return null;
}

function candidateAntennaConnector(match: Match): string | null {
  const t = candidateText(match);
  if (/\bu\.?fl\b|\bufl\b/.test(t)) return "U.FL";
  if (/antenna[- ]?pin|ant\.?\s*pins?|solder pads?/.test(t)) return "Antenna pin";
  return null;
}

function candidateAntennaCount(match: Match): number | null {
  const t = candidateText(match);
  const ufl = t.match(/\b([1-4])\s*x\s*u\.?fl\b/);
  if (ufl) return Number(ufl[1]);
  const pins = t.match(/\b([1-4])\s*(?:antenna\s*pins?|ant\.?\s*pins?)\b/);
  return pins ? Number(pins[1]) : null;
}

function candidateBluetoothVersion(match: Match): string | null {
  const t = candidateText(match);
  const patterns = [
    /bluetooth\s*([4-6](?:\.\d+)?)/,
    /\bble\s*([4-6](?:\.\d+)?)/,
    /\bbt\s*\/\s*ble\s*([4-6](?:\.\d+)?)/,
    /\bbt\s*([4-6](?:\.\d+)?)/,
  ];
  for (const pattern of patterns) {
    const m = t.match(pattern);
    if (m) return m[1];
  }
  return null;
}

function candidateGnssBand(match: Match): string | null {
  const t = candidateText(match);
  if (/\bl1\s*\+\s*l5\b|dual[- ]band\s+gnss|dual[- ]frequency\s+gnss/.test(t)) return "L1 + L5";
  if (/\bgnss\s*\(\s*l1\s*\)|\bgnss\b[^.;]{0,35}\bl1\b/.test(t)) return "L1";
  return null;
}

function candidateFormFactor(match: Match): string | null {
  const structured = match.product.features?.form_factor;
  if (structured) return structured;
  const t = candidateText(match);
  if (/\bmini\s*pcie\b/.test(t)) return "Mini PCIe";
  if (/\bm\.?2\b/.test(t)) return "M.2";
  if (/\blga\b/.test(t)) return "LGA";
  if (/\blcc\b/.test(t)) return "LCC";
  if (/\bsmd\b/.test(t)) return "SMD";
  return null;
}

function formFactorOptions(matches: Match[]): Option[] {
  const values = [...new Set(matches.map(candidateFormFactor).filter((v): v is string => !!v))];
  return [
    ...values.slice(0, 5).map((value) => ({ label: value, value })),
    { label: "No preference / not sure", value: "No preference" },
  ];
}


function tieBreakerFor(
  req: Requirements,
  topMatches: Match[]
): { key: QuestionKey; text: string; options: Option[] } | null {
  const tech = new Set(req.technologies ?? []);

  if (tech.has("wifi")) {
    if (!req.hostInterface && hasCandidateDifference(topMatches, candidateHostInterface)) {
      return {
        key: "hostInterface",
        text: "To narrow these Wi-Fi candidates down: which host interface does your system require?",
        options: [
          { label: "SDIO", value: "SDIO" },
          { label: "PCIe", value: "PCIe" },
          { label: "SDIO or PCIe", value: "SDIO or PCIe" },
          { label: "No preference / not sure", value: "No preference" },
        ],
      };
    }

    if (/small/i.test(req.specialRequirements ?? "") && !req.maxFootprint) {
      return {
        key: "maxFootprint",
        text: "You mentioned small size. Do you have a maximum module footprint?",
        options: [
          { label: "≤ 150 mm²", value: "≤ 150 mm²" },
          { label: "≤ 250 mm²", value: "≤ 250 mm²" },
          { label: "No fixed limit / not sure", value: "No fixed limit" },
        ],
      };
    }

    if (req.antenna === "external" && !req.antennaConnector &&
        hasCandidateDifference(topMatches, candidateAntennaConnector)) {
      return {
        key: "antennaConnector",
        text: "Which external antenna connection is preferred?",
        options: [
          { label: "U.FL", value: "U.FL" },
          { label: "Antenna pin / solder pad", value: "Antenna pin / solder pad" },
          { label: "No preference / not sure", value: "No preference" },
        ],
      };
    }

    if (!req.antennaCount && hasCandidateDifference(topMatches, candidateAntennaCount)) {
      return {
        key: "antennaCount",
        text: "How many external antenna connections does the design require?",
        options: [
          { label: "2 antenna connections", value: "2" },
          { label: "3 antenna connections", value: "3" },
          { label: "No preference / not sure", value: "No preference" },
        ],
      };
    }

    if (!req.bluetoothRequirement && !tech.has("bluetooth") &&
        hasCandidateDifference(topMatches, candidateBluetoothVersion)) {
      return {
        key: "bluetoothRequirement",
        text: "Should Bluetooth LE also be included in the wireless solution?",
        options: [
          { label: "Not required", value: "No requirement" },
          { label: "Yes — version open / not sure", value: "Bluetooth required, version open" },
          { label: "Bluetooth LE 5.0 or newer", value: "Bluetooth 5.0+" },
          { label: "Bluetooth LE 5.2 or newer", value: "Bluetooth 5.2+" },
          { label: "Bluetooth LE 5.3 or newer", value: "Bluetooth 5.3+" },
          { label: "Bluetooth LE 5.4 or newer", value: "Bluetooth 5.4+" },
          { label: "Bluetooth LE 6.0 or newer", value: "Bluetooth 6.0+" },
        ],
      };
    }
  }

  if (tech.has("cellular")) {
    if (!req.formFactor) {
      return {
        key: "formFactor",
        text: "Which mechanical form factor is preferred for the cellular solution?",
        options: [
          { label: "LGA module", value: "LGA" },
          { label: "Mini PCIe", value: "Mini PCIe" },
          { label: "No preference / not sure", value: "No preference" },
        ],
      };
    }

    if (tech.has("gnss") && !req.gnssDualBand) {
      return {
        key: "gnssDualBand",
        text: "Which GNSS frequency-band capability does your application need?",
        options: [
          { label: "L1 is sufficient", value: "L1 sufficient" },
          { label: "Dual-band L1 + L5 required", value: "L1 + L5 required" },
          { label: "No preference / not sure", value: "No preference" },
        ],
      };
    }
  }

  if (tech.has("gnss") && !tech.has("cellular")) {
    if (req.gnssPrecision === "cm" && !req.gnssDualBand &&
        hasCandidateDifference(topMatches, candidateGnssBand)) {
      return {
        key: "gnssDualBand",
        text: "For this high-precision GNSS application, which frequency-band capability is required?",
        options: [
          { label: "L1 is sufficient", value: "L1 sufficient" },
          { label: "Dual-band L1 + L5 required", value: "L1 + L5 required" },
          { label: "No preference / not sure", value: "No preference" },
        ],
      };
    }

    if (/small/i.test(req.specialRequirements ?? "") && !req.maxFootprint) {
      return {
        key: "maxFootprint",
        text: "You mentioned small size. What maximum GNSS module footprint would you like to target?",
        options: [
          { label: "≤ 100 mm²", value: "≤ 100 mm²" },
          { label: "≤ 150 mm²", value: "≤ 150 mm²" },
          { label: "≤ 250 mm²", value: "≤ 250 mm²" },
          { label: "No fixed limit / not sure", value: "No fixed limit" },
        ],
      };
    }

    if (!req.formFactor && hasCandidateDifference(topMatches, candidateFormFactor)) {
      return {
        key: "formFactor",
        text: "Which mechanical form factor is preferred for the GNSS receiver?",
        options: formFactorOptions(topMatches),
      };
    }
  }

  if (tech.has("bluetooth") && !tech.has("wifi")) {
    if (!req.bluetoothRequirement && hasCandidateDifference(topMatches, candidateBluetoothVersion)) {
      return {
        key: "bluetoothRequirement",
        text: "What minimum Bluetooth LE version does your application require?",
        options: [
          { label: "Version open / not sure", value: "Bluetooth required, version open" },
          { label: "Bluetooth LE 5.0 or newer", value: "Bluetooth 5.0+" },
          { label: "Bluetooth LE 5.1 or newer", value: "Bluetooth 5.1+" },
          { label: "Bluetooth LE 5.2 or newer", value: "Bluetooth 5.2+" },
          { label: "Bluetooth LE 5.3 or newer", value: "Bluetooth 5.3+" },
          { label: "Bluetooth LE 5.4 or newer", value: "Bluetooth 5.4+" },
          { label: "Bluetooth LE 6.0 or newer", value: "Bluetooth 6.0+" },
        ],
      };
    }

    if (/small/i.test(req.specialRequirements ?? "") && !req.maxFootprint) {
      return {
        key: "maxFootprint",
        text: "What maximum module footprint would you like to target?",
        options: [
          { label: "≤ 100 mm²", value: "≤ 100 mm²" },
          { label: "≤ 150 mm²", value: "≤ 150 mm²" },
          { label: "≤ 250 mm²", value: "≤ 250 mm²" },
          { label: "No fixed limit / not sure", value: "No fixed limit" },
        ],
      };
    }
  }

  return null;
}

function isMultiSelectKey(key: QuestionKey | null): boolean {
  return (
    key === "specialRequirements" ||
    key === "projectPartners" ||
    key === "technologies" ||
    key === "wifiGeneration"
  );
}

function isExclusiveMultiOption(key: QuestionKey, label: string): boolean {
  if (key === "specialRequirements") return /no special requirements/i.test(label);
  if (key === "projectPartners") return /none yet/i.test(label);
  return false;
}

function editableQuestionFor(
  key: QuestionKey,
  req: Requirements,
  currentMatches: Match[]
): { text: string; options: Option[] } | null {
  const common: Partial<Record<QuestionKey, { text: string; options: Option[] }>> = {
    productDomain: {
      text: "Update the SE product area:",
      options: DOMAIN_OPTIONS,
    },
    catalogCategory: {
      text: "Update the product type:",
      options: DOMAIN_CATEGORY_OPTIONS[req.productDomain ?? ""] ?? [],
    },
    capacitorCapacitance: {
      text: "Update the required capacitance:",
      options: [
        { label: "100 nF", value: "100 nF" },
        { label: "1 µF", value: "1 µF" },
        { label: "10 µF", value: "10 µF" },
        { label: "47 µF", value: "47 µF" },
        { label: "100 µF", value: "100 µF" },
      ],
    },
    capacitorVoltage: {
      text: "Update the minimum voltage rating:",
      options: [
        { label: "6.3 V", value: "6.3 V" },
        { label: "10 V", value: "10 V" },
        { label: "16 V", value: "16 V" },
        { label: "25 V", value: "25 V" },
        { label: "50 V", value: "50 V" },
        { label: "100 V", value: "100 V" },
      ],
    },
    capacitorTechnology: {
      text: "Update the capacitor technology:",
      options: [
        { label: "Ceramic / MLCC", value: "Ceramic" },
        { label: "Tantalum", value: "Tantalum" },
        { label: "Film", value: "Film" },
        { label: "Aluminum electrolytic", value: "Aluminum electrolytic" },
        { label: "Polymer", value: "Polymer" },
        { label: "Supercapacitor", value: "Supercapacitor" },
        { label: "No preference", value: "No preference" },
      ],
    },
    capacitorMounting: {
      text: "Update the mounting style:",
      options: [
        { label: "SMD / SMT", value: "SMD" },
        { label: "Through-hole", value: "Through-hole" },
        { label: "No preference", value: "No preference" },
      ],
    },
    capacitorTolerance: {
      text: "Update the tolerance requirement:",
      options: [
        { label: "±5%", value: "±5%" },
        { label: "±10%", value: "±10%" },
        { label: "±20%", value: "±20%" },
        { label: "No preference", value: "No preference" },
      ],
    },
    genericInterface: {
      text: "Update the preferred electrical interface / output:",
      options: [
        { label: "I²C", value: "i2c" },
        { label: "SPI", value: "spi" },
        { label: "Analog output", value: "analog" },
        { label: "Digital output", value: "digital" },
        { label: "UART", value: "uart" },
        { label: "No preference / not sure", value: "No preference" },
      ],
    },
    supportGoal: {
      text: "Update the preferred next step:",
      options: [
        { label: "Technical review with an SE FAE", value: "technical" },
        { label: "Price / availability / samples", value: "commercial" },
        { label: "No — the recommendation is enough", value: "none" },
      ],
    },
    designSituation: {
      text: "Update the project situation:",
      options: [
        { label: "New design", value: "New design" },
        { label: "Replacement / redesign", value: "Replacement / redesign" },
        { label: "Not sure yet", value: "Not sure yet" },
      ],
    },
    application: {
      text: "Update the application / use case:",
      options: [
        { label: "Asset Tracking", value: "asset tracking" },
        { label: "Industrial IoT / Gateway", value: "industrial IoT" },
        { label: "Agriculture / Precision Farming", value: "agriculture / precision farming" },
        { label: "Robotics / Autonomous", value: "robotics / autonomous" },
        { label: "Metering", value: "metering" },
        { label: "Medical / Wearable", value: "medical / wearable" },
        { label: "Industrial Storage", value: "industrial storage" },
      ],
    },
    specialRequirements: {
      text: "Update the special requirements. You can select more than one:",
      options: domainSpecialRequirementOptions(req.productDomain),
    },
    targetVolume: {
      text: "Update the planned annual production volume:",
      options: [
        { label: "< 1,000 units/year", value: "< 1,000 units/year" },
        { label: "1,000–10,000 units/year", value: "1,000–10,000 units/year" },
        { label: "10,000–100,000 units/year", value: "10,000–100,000 units/year" },
        { label: "> 100,000 units/year", value: "> 100,000 units/year" },
        { label: "Still open", value: "Still open" },
      ],
    },
    projectTimeline: {
      text: "Update the current project phase / timeline:",
      options: [
        { label: "Development", value: "Development" },
        { label: "Prototypes", value: "Prototypes" },
        { label: "Pre-series", value: "Pre-series" },
        { label: "Series production", value: "Series production" },
        { label: "Not defined yet", value: "Not defined yet" },
      ],
    },
    projectPartners: {
      text: "Update the project partners. You can select more than one:",
      options: [
        { label: "Development service provider", value: "Development service provider" },
        { label: "Manufacturer / EMS", value: "Manufacturer / EMS" },
        { label: "EMC laboratory", value: "EMC laboratory" },
        { label: "None yet", value: "None yet" },
      ],
    },
    technologies: {
      text: "Update the required technologies. You can select more than one:",
      options: [
        { label: "Cellular", value: ["cellular"] },
        { label: "Bluetooth", value: ["bluetooth"] },
        { label: "Wi-Fi", value: ["wifi"] },
        { label: "GNSS", value: ["gnss"] },
      ],
    },
    positioning: {
      text: "Update the positioning requirement:",
      options: [
        { label: "Yes, GNSS positioning", value: "yes" },
        { label: "No", value: "no" },
      ],
    },
    lowPower: {
      text: "Update the low-power requirement:",
      options: [
        { label: "Yes", value: true },
        { label: "No", value: false },
      ],
    },
    cellularClass: {
      text: "Update the cellular technology:",
      options: [
        { label: "LTE-M / NB-IoT", value: "LPWA" },
        { label: "LTE Cat 1bis", value: "Cat 1bis" },
        { label: "LTE Cat 4", value: "Cat 4" },
        { label: "5G RedCap", value: "5G RedCap" },
      ],
    },
    region: {
      text: "Update the deployment region:",
      options: [
        { label: "Global", value: "Global" },
        { label: "Americas", value: "Americas" },
        { label: "Europe / EMEA / APAC", value: "EMEA/APAC" },
      ],
    },
    architecture: {
      text: "Update the software / control architecture:",
      options: [
        { label: "Open CPU", value: "open" },
        { label: "u-connectXpress / AT commands", value: "uconnect" },
        { label: "Host-based", value: "host" },
      ],
    },
    antennaApplication: {
      text: "Update the antenna application:",
      options: [
        { label: "GNSS", value: "gnss" },
        { label: "Wi-Fi / Bluetooth", value: "wifi_bt" },
        { label: "Cellular / LTE / 5G", value: "cellular" },
        { label: "ISM / LPWAN (433 / 868 / 915 MHz)", value: "ism" },
        { label: "Multi-radio / combination", value: "multi" },
      ],
    },
    antennaGnssBand: {
      text: "Update the GNSS antenna band:",
      options: [
        { label: "GNSS L1", value: "gnss_l1" },
        { label: "GNSS multi-band (L1 + L2/L5)", value: "gnss_multiband" },
        { label: "No fixed band / not sure", value: "No preference" },
      ],
    },
    antennaWifiBand: {
      text: "Update the Wi-Fi / Bluetooth antenna band:",
      options: [
        { label: "2.4 GHz", value: "wifi_24" },
        { label: "2.4 + 5 GHz", value: "wifi_245" },
        { label: "6 GHz / Wi-Fi 6E capable", value: "wifi_6e" },
        { label: "No fixed band / not sure", value: "No preference" },
      ],
    },
    antennaActive: {
      text: "Update the GNSS antenna type:",
      options: [
        { label: "Active antenna", value: "active" },
        { label: "Passive antenna", value: "passive" },
        { label: "No preference / not sure", value: "No preference" },
      ],
    },
    antenna: {
      text: "Update the antenna approach:",
      options: [
        { label: "Integrated / PCB antenna", value: "internal" },
        { label: "External antenna / antenna pin", value: "external" },
      ],
    },
    wifiGeneration: {
      text: "Update the acceptable Wi-Fi generations:",
      options: [
        { label: "Wi-Fi 4", value: "4" },
        { label: "Wi-Fi 5", value: "5" },
        { label: "Wi-Fi 6", value: "6" },
        { label: "Wi-Fi 6E", value: "6E" },
      ],
    },
    gnssPrecision: {
      text: "Update the required positioning performance:",
      options: [
        { label: "Standard GNSS / meter-level", value: "standard" },
        { label: "High precision / centimeter-level (RTK)", value: "cm" },
        { label: "No fixed accuracy / not sure", value: "No preference" },
      ],
    },
    hostInterface: {
      text: "Update the host interface:",
      options: [
        { label: "SDIO", value: "SDIO" },
        { label: "PCIe", value: "PCIe" },
        { label: "SDIO or PCIe", value: "SDIO or PCIe" },
        { label: "No preference / not sure", value: "No preference" },
      ],
    },
    antennaConnector: {
      text: "Update the external antenna connection:",
      options: [
        { label: "U.FL", value: "U.FL" },
        { label: "Antenna pin / solder pad", value: "Antenna pin / solder pad" },
        { label: "No preference / not sure", value: "No preference" },
      ],
    },
    antennaCount: {
      text: "Update the required number of antenna connections:",
      options: [
        { label: "1 antenna connection", value: "1" },
        { label: "2 antenna connections", value: "2" },
        { label: "3 antenna connections", value: "3" },
        { label: "No preference / not sure", value: "No preference" },
      ],
    },
    bluetoothRequirement: {
      text: "Update the minimum Bluetooth LE version:",
      options: [
        { label: "Not required", value: "No requirement" },
        { label: "Version open / not sure", value: "Bluetooth required, version open" },
        { label: "Bluetooth LE 5.0 or newer", value: "Bluetooth 5.0+" },
        { label: "Bluetooth LE 5.1 or newer", value: "Bluetooth 5.1+" },
        { label: "Bluetooth LE 5.2 or newer", value: "Bluetooth 5.2+" },
        { label: "Bluetooth LE 5.3 or newer", value: "Bluetooth 5.3+" },
        { label: "Bluetooth LE 5.4 or newer", value: "Bluetooth 5.4+" },
        { label: "Bluetooth LE 6.0 or newer", value: "Bluetooth 6.0+" },
      ],
    },
    maxFootprint: {
      text: "Update the maximum module footprint:",
      options: [
        { label: "≤ 100 mm²", value: "≤ 100 mm²" },
        { label: "≤ 150 mm²", value: "≤ 150 mm²" },
        { label: "≤ 250 mm²", value: "≤ 250 mm²" },
        { label: "No fixed limit / not sure", value: "No fixed limit" },
      ],
    },
    formFactor: {
      text: "Update the preferred form factor:",
      options: [
        { label: "LGA", value: "LGA" },
        { label: "Mini PCIe", value: "Mini PCIe" },
        { label: "M.2", value: "M.2" },
        { label: "LCC", value: "LCC" },
        { label: "SMD", value: "SMD" },
        { label: "No preference / not sure", value: "No preference" },
      ],
    },
    gnssDualBand: {
      text: "Update the GNSS frequency-band requirement:",
      options: [
        { label: "L1 is sufficient", value: "L1 sufficient" },
        { label: "Dual-band L1 + L5 required", value: "L1 + L5 required" },
        { label: "No preference / not sure", value: "No preference" },
      ],
    },
  };

  if (key === "formFactor" && currentMatches.length) {
    const dynamic = formFactorOptions(currentMatches);
    if (dynamic.length > 1) return { text: "Update the preferred form factor:", options: dynamic };
  }

  return common[key] ?? null;
}

function naturalReply(key: QuestionKey, value: Option["value"]) {
  const v = valueText(value);
  const replies: Partial<Record<QuestionKey, string>> = {
    productDomain: `Good — I’ll keep the qualification focused on <strong>${htmlEscape(domainDisplayName(v))}</strong>.`,
    catalogCategory: `Understood — I’ll focus on <strong>${htmlEscape(v)}</strong>.`,
    genericInterface:
      v === "No preference"
        ? "Okay — I won’t use interface as a product filter."
        : `Good — preferred interface / output: <strong>${htmlEscape(v.toUpperCase())}</strong>.`,
    supportRequested:
      value === true
        ? "Certainly — I’ll collect a few project details for an SE follow-up."
        : "No problem — I’ll keep the conversation focused on the product recommendation.",
    supportGoal:
      v === "technical"
        ? "Good — I’ll prepare a focused technical handoff for an SE FAE."
        : v === "commercial"
          ? "Good — I’ll collect only the information needed for a price / availability follow-up."
          : "Okay — we’ll keep this as a product recommendation only.",
    supportProduct: `Understood — follow-up target: <strong>${htmlEscape(v)}</strong>.`,
    supportTopic: `Understood — FAE focus: <strong>${htmlEscape(v)}</strong>.`,
    designSituation: `Thanks — project situation: <strong>${htmlEscape(v)}</strong>.`,
    existingComponent: `Understood — existing component: <strong>${htmlEscape(v)}</strong>.`,
    application: `Got it — <strong>${htmlEscape(v)}</strong>.`,
    specialRequirements: /no special/i.test(v)
      ? "Okay — no special mechanical, power, or environmental constraint for now."
      : `Good to know — I’ll take <strong>${htmlEscape(v)}</strong> into account.`,
    targetVolume: `Thanks — planned volume: <strong>${htmlEscape(v)}</strong>.`,
    projectTimeline: `Understood — the project is currently in <strong>${htmlEscape(v)}</strong>.`,
    projectPartners: /none/i.test(v)
      ? "Okay — no external project partner is involved at the moment."
      : `Thanks — I’ll note <strong>${htmlEscape(v)}</strong>.`,
    technologies: `Perfect — I’ll focus on <strong>${htmlEscape(v)}</strong>.`,
    positioning:
      value === "yes" ? "Yes — positioning will be part of the solution." : "Okay — positioning is not required.",
    lowPower:
      value === true
        ? "That matters — I’ll favor products with stronger low-power characteristics."
        : "Okay — low power does not need to dominate the selection.",
    cellularClass: `Good — I’ll compare <strong>${htmlEscape(v)}</strong> solutions.`,
    region: `Thanks — deployment region: <strong>${htmlEscape(v)}</strong>.`,
    architecture: `Good — architecture: <strong>${htmlEscape(v)}</strong>.`,
    antenna: `Understood — antenna preference: <strong>${htmlEscape(v)}</strong>.`,
    wifiGeneration: `Good — acceptable generations: <strong>${htmlEscape(
      v.split(" + ").map((g) => `Wi-Fi ${g}`).join(" / ")
    )}</strong>.`,
    gnssPrecision:
      value === "cm"
        ? "Understood — high-precision / centimeter-level RTK positioning is required."
        : value === "standard"
          ? "Okay — standard meter-level GNSS positioning is sufficient."
          : "Okay — positioning accuracy remains open.",
    hostInterface: `Good — I’ll use <strong>${htmlEscape(v)}</strong> as the host-interface requirement.`,
    antennaConnector: `Understood — antenna connection: <strong>${htmlEscape(v)}</strong>.`,
    antennaCount: `Understood — antenna connection count: <strong>${htmlEscape(v)}</strong>.`,
    antennaApplication: `Good — antenna application: <strong>${htmlEscape(v)}</strong>.`,
    antennaGnssBand: `Understood — GNSS antenna band: <strong>${htmlEscape(v)}</strong>.`,
    antennaWifiBand: `Understood — RF coverage: <strong>${htmlEscape(v)}</strong>.`,
    antennaActive:
      v === "No preference"
        ? "Okay — active/passive remains open."
        : `Understood — GNSS antenna type: <strong>${htmlEscape(v)}</strong>.`,
    bluetoothRequirement:
      v === "Bluetooth required, version open"
        ? "Okay — Bluetooth LE is required, but the minimum version remains open."
        : v === "No requirement"
          ? "Okay — Bluetooth LE is not required."
          : `Understood — minimum requirement: <strong>${htmlEscape(v)}</strong>.`,
    maxFootprint: `Good — mechanical footprint target: <strong>${htmlEscape(v)}</strong>.`,
    formFactor: `Understood — form factor: <strong>${htmlEscape(v)}</strong>.`,
    gnssDualBand:
      v === "L1 + L5 required"
        ? "Understood — <strong>dual-band L1 + L5</strong> is required."
        : v === "L1 sufficient"
          ? "Understood — <strong>L1 is sufficient</strong>."
          : "Okay — no fixed GNSS frequency-band requirement.",
    capacitorCapacitance: `Good — required capacitance: <strong>${htmlEscape(v)}</strong>.`,
    capacitorVoltage: `Good — minimum voltage rating: <strong>${htmlEscape(v)}</strong>.`,
    capacitorTechnology:
      v === "No preference"
        ? "Okay — I won’t restrict the selection to one capacitor technology."
        : `Understood — capacitor technology: <strong>${htmlEscape(v)}</strong>.`,
    capacitorMounting:
      v === "No preference"
        ? "Okay — mounting style remains open."
        : `Understood — mounting: <strong>${htmlEscape(v)}</strong>.`,
    capacitorTolerance:
      v === "No preference"
        ? "Okay — no fixed capacitance tolerance is required."
        : `Good — tolerance requirement: <strong>${htmlEscape(v)}</strong>.`,
    capacitorCaseSize: `Case size: <strong>${htmlEscape(v)}</strong>.`,
    capacitorEsrMax: `Maximum ESR: <strong>${htmlEscape(v)}</strong>.`,
    capacitorRippleMin: `Minimum ripple current: <strong>${htmlEscape(v)}</strong>.`,
    capacitorLifetimeMin: `Minimum lifetime: <strong>${htmlEscape(v)}</strong>.`,
    capacitorTemperatureRange: `Operating temperature: <strong>${htmlEscape(v)}</strong>.`,
    capacitorEnergyMin: `Minimum stored-energy requirement: <strong>${htmlEscape(v)}</strong>.`,
  };
  return replies[key] ?? `Thanks — <strong>${htmlEscape(v)}</strong>.`;
}


function localizedNaturalReply(key: QuestionKey, value: Option["value"], language: Language) {
  if (language === "en") return naturalReply(key, value);

  const v = valueText(value);
  const generic: Partial<Record<QuestionKey, string>> = {
    productDomain: "Gut — ich fokussiere die Auswahl auf den gewählten Produktbereich.",
    catalogCategory: `Verstanden — ich berücksichtige <strong>${htmlEscape(OPTION_DE[v] ?? v)}</strong>.`,
    genericInterface: v === "No preference"
      ? "Okay — die Schnittstelle wird nicht als Filter verwendet."
      : `Gut — bevorzugte Schnittstelle: <strong>${htmlEscape(v.toUpperCase())}</strong>.`,
    technologies: "Verstanden — die ausgewählten Technologien werden berücksichtigt.",
    specialRequirements: "Danke — die Designvorgaben sind berücksichtigt.",
    positioning: v === "yes" ? "Verstanden — GNSS-Positionierung wird berücksichtigt." : "Verstanden — keine zusätzliche GNSS-Positionierung.",
    lowPower: value === true ? "Verstanden — geringer Stromverbrauch ist wichtig." : "Verstanden.",
    cellularClass: `Mobilfunkklasse: <strong>${htmlEscape(v)}</strong>.`,
    region: `Einsatzregion: <strong>${htmlEscape(v)}</strong>.`,
    architecture: `Architektur: <strong>${htmlEscape(v)}</strong>.`,
    antenna: `Antennenvariante: <strong>${htmlEscape(v)}</strong>.`,
    wifiGeneration: `Geeignete Wi-Fi-Generationen: <strong>${htmlEscape(
      v.split(" + ").map((g) => `Wi-Fi ${g}`).join(" / ")
    )}</strong>.`,
    gnssPrecision: `GNSS-Genauigkeit: <strong>${htmlEscape(v)}</strong>.`,
    supportRequested: value === true
      ? "Gerne — ich erfasse noch einige Projektdaten für die SE-Unterstützung."
      : "Kein Problem — die Produktempfehlung bleibt im Fokus.",
    supportGoal: v === "technical"
      ? "Gut — ich bereite eine gezielte technische Übergabe an einen SE FAE vor."
      : v === "commercial"
        ? "Gut — ich erfasse nur die Angaben für Preis / Verfügbarkeit."
        : "Okay — wir belassen es bei der Produktempfehlung.",
    supportProduct: `Follow-up für: <strong>${htmlEscape(v)}</strong>.`,
    supportTopic: `FAE-Fokus: <strong>${htmlEscape(v)}</strong>.`,
    designSituation: `Projektsituation: <strong>${htmlEscape(OPTION_DE[v] ?? v)}</strong>.`,
    existingComponent: `Bestehende Komponente: <strong>${htmlEscape(v)}</strong>.`,
    targetVolume: `Geplante Jahresmenge: <strong>${htmlEscape(v)}</strong>.`,
    projectTimeline: `Projektphase: <strong>${htmlEscape(OPTION_DE[v] ?? v)}</strong>.`,
    projectPartners: "Danke — die Projektpartner sind erfasst.",
    hostInterface: `Host-Schnittstelle: <strong>${htmlEscape(v)}</strong>.`,
    antennaConnector: `Antennenanschluss: <strong>${htmlEscape(v)}</strong>.`,
    antennaCount: `Antennenanschlüsse: <strong>${htmlEscape(v)}</strong>.`,
    antennaApplication: `Antennenanwendung: <strong>${htmlEscape(v)}</strong>.`,
    antennaGnssBand: `GNSS-Antennenband: <strong>${htmlEscape(v)}</strong>.`,
    antennaWifiBand: `HF-Abdeckung: <strong>${htmlEscape(v)}</strong>.`,
    antennaActive: v === "No preference"
      ? "Okay — aktiv/passiv bleibt offen."
      : `GNSS-Antennentyp: <strong>${htmlEscape(v)}</strong>.`,
    bluetoothRequirement: `Bluetooth-Anforderung: <strong>${htmlEscape(v)}</strong>.`,
    maxFootprint: `Maximale Fläche: <strong>${htmlEscape(v)}</strong>.`,
    formFactor: `Bauform: <strong>${htmlEscape(v)}</strong>.`,
    gnssDualBand: `GNSS-Bänder: <strong>${htmlEscape(v)}</strong>.`,
    capacitorCapacitance: `Kapazität: <strong>${htmlEscape(v)}</strong>.`,
    capacitorVoltage: `Nennspannung mindestens: <strong>${htmlEscape(v)}</strong>.`,
    capacitorTechnology: v === "No preference"
      ? "Okay — keine feste Kondensatortechnologie."
      : `Kondensatortechnologie: <strong>${htmlEscape(v)}</strong>.`,
    capacitorMounting: v === "No preference"
      ? "Okay — Montageart bleibt offen."
      : `Montage: <strong>${htmlEscape(v)}</strong>.`,
    capacitorTolerance: v === "No preference"
      ? "Okay — keine feste Toleranzvorgabe."
      : `Toleranz: <strong>${htmlEscape(v)}</strong>.`,
    capacitorCaseSize: `Baugröße: <strong>${htmlEscape(v)}</strong>.`,
    capacitorEsrMax: `Maximaler ESR: <strong>${htmlEscape(v)}</strong>.`,
    capacitorRippleMin: `Minimaler Ripple-Strom: <strong>${htmlEscape(v)}</strong>.`,
    capacitorLifetimeMin: `Mindestlebensdauer: <strong>${htmlEscape(v)}</strong>.`,
    capacitorTemperatureRange: `Temperaturbereich: <strong>${htmlEscape(v)}</strong>.`,
    capacitorEnergyMin: `Mindestenergie: <strong>${htmlEscape(v)}</strong>.`,
  };
  return generic[key] ?? "Verstanden.";
}


function buildMatchBody(req: Requirements) {
  const bluetoothRequired =
    req.bluetoothRequirement && req.bluetoothRequirement !== "No requirement"
      ? true
      : null;

  const btMin =
    req.bluetoothRequirement?.match(/Bluetooth\s+([4-6](?:\.\d+)?)\+/i)?.[1] ?? null;

  const maxFootprint =
    req.maxFootprint && req.maxFootprint !== "No fixed limit"
      ? Number(req.maxFootprint.match(/(\d+(?:\.\d+)?)/)?.[1] ?? 0) || null
      : null;

  const effectiveTechnologies = bluetoothRequired
    ? [...new Set([...(req.technologies ?? []), "bluetooth"])]
    : req.technologies ?? [];

  return {
    application: req.application ?? null,
    product_domain: req.productDomain ?? null,
    catalog_category: req.catalogCategory ?? null,
    generic_interface:
      req.genericInterface && req.genericInterface !== "No preference"
        ? req.genericInterface
        : null,
    technologies: effectiveTechnologies,
    cellular_class: req.cellularClass ?? null,
    region: req.region ?? null,
    architecture: req.architecture ?? null,
    antenna: req.antenna ?? null,
    wifi_generation: req.wifiGeneration ?? [],
    gnss_precision:
      req.gnssPrecision && req.gnssPrecision !== "No preference"
        ? req.gnssPrecision
        : null,
    low_power: req.lowPower ?? null,
    host_interface:
      req.hostInterface === "SDIO" ? "sdio" :
      req.hostInterface === "PCIe" ? "pcie" :
      req.hostInterface === "SDIO or PCIe" ? "sdio_pcie" : null,
    antenna_connector:
      req.antennaConnector === "U.FL" ? "ufl" :
      req.antennaConnector === "Antenna pin / solder pad" ? "antenna_pin" : null,
    antenna_count:
      req.antennaCount && req.antennaCount !== "No preference"
        ? Number(req.antennaCount)
        : null,
    antenna_application: req.antennaApplication ?? null,
    antenna_band:
      req.antennaBand && req.antennaBand !== "No preference"
        ? req.antennaBand
        : null,
    antenna_active:
      req.antennaActive === "active" ? true :
      req.antennaActive === "passive" ? false :
      null,
    bluetooth_required: bluetoothRequired,
    bluetooth_version_min: btMin,
    max_footprint_mm2: maxFootprint,
    form_factor:
      req.formFactor && req.formFactor !== "No preference"
        ? req.formFactor
        : null,
    gnss_dual_band:
      req.gnssDualBand === "L1 + L5 required" ? true :
      req.gnssDualBand === "L1 sufficient" ? false :
      null,

    engineering_requirements: Object.fromEntries(
      Object.entries(req.engineering ?? {}).filter(([, value]) => value !== "__open__")
    ),
    answered_engineering_fields: req.answeredEngineering ?? [],

    capacitance_uf:
      req.capacitorCapacitance ? parseCapacitanceUf(req.capacitorCapacitance) : null,
    capacitor_voltage_v:
      req.capacitorVoltage ? parseSimpleNumber(req.capacitorVoltage) : null,
    capacitor_tolerance_pct:
      req.capacitorTolerance && req.capacitorTolerance !== "No preference"
        ? parseSimpleNumber(req.capacitorTolerance)
        : null,
    capacitor_technology:
      req.capacitorTechnology && req.capacitorTechnology !== "No preference"
        ? req.capacitorTechnology
        : null,
    capacitor_mounting:
      req.capacitorMounting && req.capacitorMounting !== "No preference"
        ? req.capacitorMounting
        : null,
    capacitor_case_size: req.capacitorCaseSize ?? null,
    capacitor_esr_max_ohm:
      req.capacitorEsrMax ? parseSimpleNumber(req.capacitorEsrMax) : null,
    capacitor_ripple_current_min_a:
      req.capacitorRippleMin ? parseSimpleNumber(req.capacitorRippleMin) : null,
    capacitor_lifetime_min_h:
      req.capacitorLifetimeMin
        ? Math.round(parseSimpleNumber(req.capacitorLifetimeMin) ?? 0) || null
        : null,
    capacitor_temperature_min_c:
      req.capacitorTemperatureRange
        ? Number(
            req.capacitorTemperatureRange
              .match(/-?\d+(?:[.,]\d+)?/)?.[0]
              .replace(",", ".") ?? ""
          ) || null
        : null,
    capacitor_temperature_max_c:
      req.capacitorTemperatureRange
        ? (() => {
            const values = [
              ...req.capacitorTemperatureRange.matchAll(/-?\d+(?:[.,]\d+)?/g),
            ].map((m) => Number(m[0].replace(",", ".")));
            return values.length >= 2 ? values[1] : null;
          })()
        : null,
    capacitor_energy_min_j:
      req.capacitorEnergyMin ? parseSimpleNumber(req.capacitorEnergyMin) : null,
    mandatory: [],
    answered_open_fields: [
      ...(req.hostInterface === "No preference" ? ["hostInterface"] : []),
      ...(req.antennaConnector === "No preference" ? ["antennaConnector"] : []),
      ...(req.antennaCount === "No preference" ? ["antennaCount"] : []),
      ...(req.antennaBand === "No preference"
        ? [req.antennaApplication === "gnss" ? "antennaGnssBand" : "antennaWifiBand"]
        : []),
      ...(req.antennaActive === "No preference" ? ["antennaActive"] : []),
      ...(req.formFactor === "No preference" ? ["formFactor"] : []),
      ...(req.maxFootprint === "No fixed limit" ? ["maxFootprint"] : []),
    ],
  };
}


async function adaptiveQuestionWithBackend(
  req: Requirements
): Promise<AdaptiveQuestionResponse> {
  const response = await fetch(`${API}/api/requirements/adaptive-question`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requirements: buildMatchBody(req) }),
  });

  if (!response.ok) {
    throw new Error(`Adaptive question HTTP ${response.status}`);
  }

  return response.json();
}


type MatchGroup = {
  key: string;
  primary: Match;
  variants: Match[];
};

function groupMatchesByVerifiedFamily(matches: Match[]): MatchGroup[] {
  const groups = new Map<string, MatchGroup>();

  for (const match of matches) {
    const familyUsable =
      match.family &&
      match.family.verification_status === "verified" &&
      match.family.member_count >= 2;

    const key = familyUsable
      ? `family:${match.family!.id}`
      : `product:${match.product.id}`;

    const current = groups.get(key);
    if (!current) {
      groups.set(key, {
        key,
        primary: match,
        variants: [match],
      });
      continue;
    }

    current.variants.push(match);

    // Backend is already ranked, but keep this helper safe for reused data.
    if (
      match.match_percent > current.primary.match_percent ||
      (
        match.match_percent === current.primary.match_percent &&
        (
          match.solution_scope_score > current.primary.solution_scope_score ||
          (
            match.solution_scope_score === current.primary.solution_scope_score &&
            match.evidence_score > current.primary.evidence_score
          )
        )
      )
    ) {
      current.primary = match;
    }
  }

  return [...groups.values()];
}

function uniqueSolutionMatches(matches: Match[]): Match[] {
  return groupMatchesByVerifiedFamily(matches).map((group) => group.primary);
}


function App() {
  const [language, setLanguage] = useState<Language>("en");
  const [viewMode, setViewMode] = useState<ViewMode>("customer");
  const developerModeAvailable = import.meta.env.DEV;
  const [backend, setBackend] = useState<"checking" | "connected" | "offline">("checking");
  const [requirements, setRequirements] = useState<Requirements>({});
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeQuestion, setActiveQuestion] = useState<QuestionKey | null>(null);
  const [quickOptions, setQuickOptions] = useState<Option[]>([]);
  const [multiSelected, setMultiSelected] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [matches, setMatches] = useState<Match[]>([]);
  const [showAllResults, setShowAllResults] = useState(false);
  const [matching, setMatching] = useState(false);
  const [finished, setFinished] = useState(false);
  const [catalogStatus, setCatalogStatus] = useState<{total_products:number;structured_products:number;live_imported_products:number;catalog_sections_configured:number} | null>(null);
  const messageId = useRef(0);
  const chatBodyRef = useRef<HTMLDivElement | null>(null);
  const firstRecommendationRef = useRef<HTMLElement | null>(null);
  const focusResultsAfterMatch = useRef(false);
  const adaptiveQuestionRequestId = useRef(0);

  const addMessage = (role: Role, html: string) => {
    setMessages((old) => [...old, { id: ++messageId.current, role, html }]);
  };

  const askNext = async (
    nextReq: Requirements,
    selectedLanguage: Language = language
  ) => {
    const fallback = localizeQuestion(questionFor(nextReq), selectedLanguage);

    // These structural questions establish enough context before asking the
    // catalog which engineering detail is most informative.
    const structuralKeys = new Set<QuestionKey>([
      "initialNeed",
      "productDomain",
      "catalogCategory",
      "technologies",
    ]);

    const showQuestion = (
      q: { key: QuestionKey; text: string; options?: Option[] },
      adaptive?: AdaptiveQuestionResponse["question"]
    ) => {
      setActiveQuestion(q.key);
      setQuickOptions(q.options ?? []);
      setMultiSelected([]);

      let text = q.text;
      if (adaptive && adaptive.candidate_count > 1) {
        const customerHint =
          adaptive.mode === "tie_break"
            ? tr(
                selectedLanguage,
                `This detail can distinguish ${adaptive.top_tie_count} top-ranked candidates that are still technically tied.`,
                `Diese Angabe kann ${adaptive.top_tie_count} weiterhin technisch gleichauf liegende Top-Kandidaten unterscheiden.`
              )
            : tr(
                selectedLanguage,
                `This is the most useful next detail for narrowing ${adaptive.candidate_count} remaining candidates.`,
                `Diese Angabe hilft am besten, die ${adaptive.candidate_count} verbleibenden Kandidaten einzugrenzen.`
              );

        const developerHint =
          viewMode === "developer"
            ? tr(
                selectedLanguage,
                ` Information gain: ${adaptive.information_gain.toFixed(2)} bits · catalog coverage: ${Math.round(adaptive.known_coverage * 100)}% · mode: ${adaptive.mode}.`,
                ` Informationsgewinn: ${adaptive.information_gain.toFixed(2)} Bit · Katalogabdeckung: ${Math.round(adaptive.known_coverage * 100)} % · Modus: ${adaptive.mode}.`
              )
            : "";

        text += `<br><span class='botHint'>${customerHint}${developerHint}</span>`;
      }

      addMessage("bot", text);
    };

    if (fallback && structuralKeys.has(fallback.key)) {
      showQuestion(fallback);
      return;
    }

    const requestId = ++adaptiveQuestionRequestId.current;

    try {
      const adaptive = await adaptiveQuestionWithBackend(nextReq);
      if (requestId !== adaptiveQuestionRequestId.current) return;

      if (adaptive.question) {
        const localized = localizeQuestion(
          {
            key: adaptive.question.key,
            text: adaptive.question.text,
            options: adaptive.question.options,
          },
          selectedLanguage
        );
        if (localized) {
          showQuestion(localized, adaptive.question);
          return;
        }
      }

      // Backend was reachable and found no further useful/required engineering
      // question for the current candidate set.
      setActiveQuestion(null);
      setQuickOptions([]);
      void runMatch(nextReq);
      return;
    } catch {
      // If adaptive analysis is unavailable, preserve the deterministic local
      // flow rather than blocking the customer.
      if (fallback) {
        showQuestion(fallback);
        return;
      }

      setActiveQuestion(null);
      setQuickOptions([]);
      void runMatch(nextReq);
    }
  };


  const askCommercialNext = (nextReq: Requirements, selectedLanguage: Language = language) => {
    const q = localizeQuestion(commercialQuestionFor(nextReq, matches), selectedLanguage);
    if (!q) {
      setActiveQuestion(null);
      setQuickOptions([]);
      setMultiSelected([]);

      if (nextReq.supportGoal === "technical") {
        addMessage(
          "bot",
          tr(
            selectedLanguage,
            `FAE handoff context is ready: <strong>${htmlEscape(nextReq.supportProduct ?? "top recommendation")}</strong>${nextReq.supportTopic ? ` · ${htmlEscape(nextReq.supportTopic)}` : ""}. These handoff details do <strong>not</strong> change the technical ranking. Use <strong>Ask an FAE</strong> on the preferred product card to continue.`,
            `Der FAE-Übergabekontext ist vorbereitet: <strong>${htmlEscape(nextReq.supportProduct ?? "Top-Empfehlung")}</strong>${nextReq.supportTopic ? ` · ${htmlEscape(nextReq.supportTopic)}` : ""}. Diese Übergabeangaben ändern das technische Ranking <strong>nicht</strong>. Nutzen Sie <strong>Ask an FAE</strong> bei der gewünschten Produktkarte.`
          )
        );
      } else if (nextReq.supportGoal === "commercial") {
        addMessage(
          "bot",
          tr(
            selectedLanguage,
            `Commercial follow-up context is ready: <strong>${htmlEscape(nextReq.supportProduct ?? "top recommendation")}</strong>${nextReq.targetVolume ? ` · ${htmlEscape(nextReq.targetVolume)}` : ""}${nextReq.projectTimeline ? ` · ${htmlEscape(nextReq.projectTimeline)}` : ""}. These details do <strong>not</strong> change the technical ranking.`,
            `Der kaufmännische Follow-up-Kontext ist vorbereitet: <strong>${htmlEscape(nextReq.supportProduct ?? "Top-Empfehlung")}</strong>${nextReq.targetVolume ? ` · ${htmlEscape(nextReq.targetVolume)}` : ""}${nextReq.projectTimeline ? ` · ${htmlEscape(nextReq.projectTimeline)}` : ""}. Diese Angaben ändern das technische Ranking <strong>nicht</strong>.`
          )
        );
      } else if (nextReq.supportGoal === "none") {
        addMessage(
          "bot",
          tr(
            selectedLanguage,
            "No problem. You can edit a technical requirement, inspect the sources, or start another request.",
            "Kein Problem. Sie können eine technische Anforderung bearbeiten, die Quellen prüfen oder eine neue Anfrage starten."
          )
        );
      }
      return;
    }

    setActiveQuestion(q.key);
    setQuickOptions(q.options ?? []);
    setMultiSelected([]);
    addMessage("bot", q.text);
  };

  const offerProjectSupport = (nextReq: Requirements) => {
    if (nextReq.supportGoal !== undefined) return;
    window.setTimeout(() => askCommercialNext(nextReq), 80);
  };

  const switchLanguage = (nextLanguage: Language) => {
    if (nextLanguage === language) return;
    setLanguage(nextLanguage);
    document.documentElement.lang = nextLanguage;

    adaptiveQuestionRequestId.current += 1;
    setRequirements({});
    setMatches([]);
    setShowAllResults(false);
    setFinished(false);
    setMessages([]);
    setQuickOptions([]);
    setMultiSelected([]);
    setActiveQuestion(null);
    window.setTimeout(() => void askNext({}, nextLanguage), 30);
  };

  const reset = () => {
    adaptiveQuestionRequestId.current += 1;
    setRequirements({});
    setMatches([]);
    setShowAllResults(false);
    setFinished(false);
    setMessages([]);
    setQuickOptions([]);
    setMultiSelected([]);
    setActiveQuestion(null);
    window.setTimeout(() => void askNext({}), 30);
  };

  useEffect(() => {
    document.documentElement.lang = language;
    fetch(`${API}/api/health`)
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then(() => setBackend("connected"))
      .catch(() => setBackend("offline"));

    fetch(`${API}/api/catalog/status`)
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((data) => setCatalogStatus(data))
      .catch(() => setCatalogStatus(null));

    window.setTimeout(() => void askNext({}), 50);
  }, []);

  useEffect(() => {
    // Keep conversation scrolling inside the chat panel. This avoids moving
    // the whole browser window toward the bottom of the page.
    const el = chatBodyRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, quickOptions]);

  useEffect(() => {
    if (matching || !matches.length || !focusResultsAfterMatch.current) return;

    focusResultsAfterMatch.current = false;

    // Let React paint the new ranking first, then bring recommendation #1
    // into view so the customer immediately sees the best result.
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        firstRecommendationRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    });
  }, [matching, matches]);

  const completeness = useMemo(() => {
    const expected = ["productDomain"];

    if (requirements.productDomain === "connectivity") {
      expected.push("technologies");
      if (requirements.application === "asset tracking") expected.push("lowPower");
      if (requirements.technologies?.includes("cellular")) expected.push("cellularClass", "region");
      if (requirements.technologies?.includes("wifi")) expected.push("architecture", "wifiGeneration");
      if (requirements.technologies?.includes("bluetooth"))
        expected.push("architecture", "bluetoothRequirement", "antenna");
      if (requirements.technologies?.includes("gnss"))
        expected.push("gnssPrecision", "gnssDualBand");
    } else if (requirements.productDomain === "positioning") {
      expected.push("gnssPrecision", "gnssDualBand");
    } else if (requirements.productDomain === "antenna") {
      expected.push("catalogCategory", "antennaApplication");
      if (requirements.antennaApplication === "gnss") {
        expected.push("antennaBand", "antennaActive");
      }
      if (requirements.antennaApplication === "wifi_bt") {
        expected.push("antennaBand");
      }
    } else if (DOMAIN_CATEGORY_OPTIONS[requirements.productDomain ?? ""]?.length) {
      expected.push("catalogCategory");
      if (requirements.productDomain === "sensors") expected.push("genericInterface");
      if (requirements.catalogCategory === "Capacitors") {
        expected.push(
          "capacitorCapacitance",
          "capacitorVoltage",
          "capacitorTechnology",
          "capacitorMounting",
          "capacitorTolerance"
        );
      }
    }

    const unique = [...new Set(expected)];
    const done = unique.filter((k) => {
      const value = requirements[k as keyof Requirements];
      return value !== undefined && value !== null && value !== "";
    }).length;
    return Math.round((done / unique.length) * 100);
  }, [requirements]);

  async function runMatch(req: Requirements, refinement = false) {
    if (!req.technologies?.length && !req.catalogCategory) return;
    focusResultsAfterMatch.current = true;
    setMatching(true);
    setShowAllResults(false);
    setFinished(false);
    addMessage(
      "bot",
      refinement
        ? tr(language, "Thanks — I’ll use that technical detail to refine the ranking.", "Danke — ich nutze dieses technische Detail, um die Auswahl weiter einzugrenzen.")
        : tr(language, "Thanks — I have enough information now. I’m comparing the requirements against the SE product database.", "Danke — die technischen Angaben reichen für einen ersten Vergleich aus. Ich gleiche sie jetzt mit der SE-Produktdatenbank ab.")
    );

    const body = buildMatchBody(req);

    try {
      const response = await fetch(`${API}/api/match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data: MatchResponse = await response.json();
      setMatches(data.matches);
      setFinished(true);

      if (data.matches.length) {
        const solutionMatches = uniqueSolutionMatches(data.matches);
        const best = solutionMatches[0];
        const topMatches = solutionMatches.filter(
          (m) =>
            m.match_percent === best.match_percent &&
            m.solution_scope_score === best.solution_scope_score
        );

        if (topMatches.length === 1) {
          if (best.recommendation_confidence === "fae_verification_required") {
            const issueText = best.verification_issues.length
              ? best.verification_issues.map((item) => htmlEscape(item)).join(", ")
              : tr(language, "one or more requested specifications", "eine oder mehrere angefragte Spezifikationen");

            addMessage(
              "bot",
              language === "de"
                ? `<strong>${htmlEscape(best.product.part_number)}</strong> von <strong>${htmlEscape(
                    best.product.manufacturer
                  )}</strong> ist mit <strong>${best.match_percent}%</strong> aktuell der stärkste <strong>vorläufige</strong> Treffer. Mindestens eine angefragte Eigenschaft konnte jedoch noch nicht sicher bestätigt werden: <strong>${issueText}</strong>. Eine Prüfung anhand der technischen Dokumentation bzw. durch einen SE FAE wird vor dem Design-in empfohlen.`
                : `<strong>${htmlEscape(best.product.part_number)}</strong> from <strong>${htmlEscape(
                    best.product.manufacturer
                  )}</strong> is currently the strongest <strong>provisional</strong> match at <strong>${best.match_percent}%</strong>. However, at least one requested specification is not yet confirmed: <strong>${issueText}</strong>. Datasheet / SE FAE verification is recommended before design-in.`
            );
          } else if (best.recommendation_confidence === "provisional_fit") {
            addMessage(
              "bot",
              language === "de"
                ? `Auf Basis der erfassten Anforderungen ist <strong>${htmlEscape(best.product.part_number)}</strong> von <strong>${htmlEscape(
                    best.product.manufacturer
                  )}</strong> aktuell der stärkste <strong>vorläufige</strong> technische Treffer mit <strong>${best.match_percent}%</strong>. Die aktuellen SE-Katalog- bzw. strukturierten Produktdaten stützen die Eignung; die Verifikation anhand der Herstellerdokumentation ist noch nicht vollständig.`
                : `Based on the collected requirements, <strong>${htmlEscape(best.product.part_number)}</strong> from <strong>${htmlEscape(
                    best.product.manufacturer
                  )}</strong> is currently the strongest <strong>provisional</strong> technical match at <strong>${best.match_percent}%</strong>. The current SE catalog / structured product data supports the fit; manufacturer-document verification is not yet complete.`
            );
          } else {
            addMessage(
              "bot",
              language === "de"
                ? `Auf Basis der erfassten Anforderungen ist <strong>${htmlEscape(best.product.part_number)}</strong> von <strong>${htmlEscape(
                    best.product.manufacturer
                  )}</strong> aktuell die technisch passendste <strong>verifizierte</strong> Empfehlung mit <strong>${best.match_percent}%</strong>.`
                : `Based on the collected requirements, <strong>${htmlEscape(best.product.part_number)}</strong> from <strong>${htmlEscape(
                    best.product.manufacturer
                  )}</strong> is currently the strongest <strong>verified</strong> technical match at <strong>${best.match_percent}%</strong>.`
            );
          }
          offerProjectSupport(req);
        } else {
          addMessage(
            "bot",
            language === "de"
              ? `<strong>${topMatches.length} Produkte</strong> erreichen denselben technischen Spitzenwert von <strong>${best.match_percent}%</strong>. Ich wähle keines willkürlich aus, solange die aktuellen Anforderungen sie technisch nicht unterscheiden.`
              : `<strong>${topMatches.length} products</strong> share the highest technical score of <strong>${best.match_percent}%</strong>. I won’t select one arbitrarily when the current requirements do not technically distinguish them.`
          );

          const tieQuestion = localizeQuestion(tieBreakerFor(req, topMatches), language);
          if (tieQuestion) {
            setFinished(false);
            setActiveQuestion(tieQuestion.key);
            setQuickOptions(tieQuestion.options ?? []);
            setMultiSelected([]);
            addMessage("bot", tieQuestion.text);
          } else {
            addMessage(
              "bot",
              tr(
                language,
                "The remaining products are technically equivalent for the requirements collected so far. If needed, I would compare the detailed technical documentation or involve an SE FAE rather than invent a technical winner.",
                "Die verbleibenden Produkte sind für die bisher erfassten Anforderungen technisch gleichwertig. Falls nötig, sollte die detaillierte Dokumentation verglichen oder ein SE FAE einbezogen werden, anstatt einen technischen Sieger zu erfinden."
              )
            );

            if (req.lowPower && topMatches.some((m) => m.reasons.some((r) => /not verified: low-power/i.test(r)))) {
              addMessage(
                "bot",
                tr(
                  language,
                  "Low-power behavior is not verified from the current catalog text for at least one top candidate. Current-consumption and sleep-mode data should be confirmed from the datasheet before design-in.",
                  "Bei mindestens einem Top-Kandidaten sollten Stromaufnahme und Sleep-Mode-Daten vor dem Design-in anhand des Datenblatts bestätigt werden."
                )
              );
            }
            offerProjectSupport(req);
          }
        }
      } else {
        addMessage(
          "bot",
          tr(
            language,
            "I don’t see a product in the current database that satisfies the collected mandatory requirements. I would hand this requirement profile to an SE FAE rather than force a weak recommendation.",
            "In der aktuellen Datenbank finde ich kein Produkt, das die erfassten Muss-Anforderungen erfüllt. Ich würde das Anforderungsprofil an einen SE FAE übergeben, statt eine schwache Empfehlung zu erzwingen."
          )
        );
        offerProjectSupport(req);
      }
    } catch {
      setBackend("offline");
      addMessage(
        "bot",
        tr(
          language,
          "I can’t reach the FastAPI backend right now. Please make sure the backend PowerShell window is still running on port 8000.",
          "Das Backend ist momentan nicht erreichbar. Bitte prüfen Sie, ob das FastAPI-PowerShell-Fenster weiterhin auf Port 8000 läuft."
        )
      );
    } finally {
      setMatching(false);
    }
  }


  function toggleMultiOption(option: Option) {
    if (!activeQuestion || !isMultiSelectKey(activeQuestion)) return;

    setMultiSelected((current) => {
      const selected = current.includes(option.label);

      if (isExclusiveMultiOption(activeQuestion, option.label)) {
        return selected ? [] : [option.label];
      }

      const withoutExclusive = current.filter(
        (label) => !isExclusiveMultiOption(activeQuestion, label)
      );

      return selected
        ? withoutExclusive.filter((label) => label !== option.label)
        : [...withoutExclusive, option.label];
    });
  }

  function confirmMultiSelection() {
    if (!activeQuestion || !isMultiSelectKey(activeQuestion) || !multiSelected.length) return;

    const selectedOptions = quickOptions.filter((option) => multiSelected.includes(option.label));
    const shown = selectedOptions.map((option) => option.label).join(" + ");

    if (activeQuestion === "technologies" || activeQuestion === "wifiGeneration") {
      const values = [
        ...new Set(
          selectedOptions.flatMap((option) =>
            Array.isArray(option.value) ? option.value.map(String) : [String(option.value)]
          )
        ),
      ];
      void applyAnswer(activeQuestion, values, shown);
      return;
    }

    void applyAnswer(
      activeQuestion,
      selectedOptions.map((option) => String(option.value)),
      shown
    );
  }

  async function applyAnswer(key: QuestionKey, value: Option["value"], shownText?: string) {
    const shown = shownText ?? valueText(value);
    addMessage("user", htmlEscape(shown));

    if (key === "initialNeed") {
      const text = String(value);
      let inferred: Partial<Requirements>;

      try {
        inferred = await interpretWithBackend(text);
      } catch {
        // Development fallback if the interpretation endpoint is temporarily unavailable.
        inferred = inferFromText(text);
      }

      const next = { ...requirements, ...inferred, initialNeed: text };
      if (inferred.lowPower) {
        next.specialRequirements = next.specialRequirements ?? "Battery powered / Low power";
      }
      setRequirements(next);
      setQuickOptions([]);
      setActiveQuestion(null);
      window.setTimeout(() => void askNext(next), 60);
      return;
    }

    if (key.startsWith("engineering:")) {
      const field = key.slice("engineering:".length);
      const next: Requirements = {
        ...requirements,
        engineering: { ...(requirements.engineering ?? {}) },
        answeredEngineering: [...(requirements.answeredEngineering ?? [])],
      };

      if (String(value) === "__open__") {
        delete next.engineering?.[field];
        next.answeredEngineering = [...new Set([...(next.answeredEngineering ?? []), field])];
        addMessage(
          "bot",
          tr(
            language,
            `Okay — <strong>${htmlEscape(engineeringRequirementLabel(field, language))}</strong> remains open and will not be used as a hard filter.`,
            `Okay — <strong>${htmlEscape(engineeringRequirementLabel(field, language))}</strong> bleibt offen und wird nicht als harter Filter verwendet.`
          )
        );
      } else {
        if (next.engineering) next.engineering[field] = value as string | number | boolean;
        next.answeredEngineering = (next.answeredEngineering ?? []).filter((item) => item !== field);
        addMessage(
          "bot",
          tr(
            language,
            `Good — <strong>${htmlEscape(engineeringRequirementLabel(field, language))}</strong>: <strong>${htmlEscape(shown)}</strong>.`,
            `Gut — <strong>${htmlEscape(engineeringRequirementLabel(field, language))}</strong>: <strong>${htmlEscape(shown)}</strong>.`
          )
        );
      }

      setRequirements(next);
      setQuickOptions([]);
      setMultiSelected([]);
      setActiveQuestion(null);
      window.setTimeout(() => void askNext(next), 60);
      return;
    }

    const next: Requirements = { ...requirements };

    switch (key) {
      case "productDomain": {
        next.productDomain = String(value);
        next.catalogCategory = undefined;
        next.genericInterface = undefined;
        next.technologies = defaultTechnologiesForDomain(next.productDomain);
        next.capacitorCapacitance = undefined;
        next.capacitorVoltage = undefined;
        next.capacitorTechnology = undefined;
        next.capacitorMounting = undefined;
        next.capacitorTolerance = undefined;
        next.capacitorCaseSize = undefined;
        next.capacitorEsrMax = undefined;
        next.capacitorRippleMin = undefined;
        next.capacitorLifetimeMin = undefined;
        next.capacitorTemperatureRange = undefined;
        next.capacitorEnergyMin = undefined;
        next.antennaApplication = undefined;
        next.antennaBand = undefined;
        next.antennaActive = undefined;
        next.engineering = undefined;
        next.answeredEngineering = undefined;

        if (next.productDomain !== "connectivity") {
          next.cellularClass = undefined;
          next.region = undefined;
          next.architecture = undefined;
          next.antenna = undefined;
          next.wifiGeneration = undefined;
          next.hostInterface = undefined;
          next.antennaConnector = undefined;
          next.antennaCount = undefined;
          next.bluetoothRequirement = undefined;
        }

        if (next.productDomain === "connectivity") {
          next.technologies = [];
        }
        break;
      }
      case "catalogCategory":
        next.catalogCategory = String(value);
        next.engineering = undefined;
        next.answeredEngineering = undefined;
        if (next.catalogCategory !== "Capacitors") {
          next.capacitorCapacitance = undefined;
          next.capacitorVoltage = undefined;
          next.capacitorTechnology = undefined;
          next.capacitorMounting = undefined;
          next.capacitorTolerance = undefined;
          next.capacitorCaseSize = undefined;
          next.capacitorEsrMax = undefined;
          next.capacitorRippleMin = undefined;
          next.capacitorLifetimeMin = undefined;
          next.capacitorTemperatureRange = undefined;
          next.capacitorEnergyMin = undefined;
        }
        break;
      case "capacitorCapacitance":
        next.capacitorCapacitance = String(value);
        break;
      case "capacitorVoltage":
        next.capacitorVoltage = String(value);
        break;
      case "capacitorTechnology":
        next.capacitorTechnology = String(value);
        break;
      case "capacitorMounting":
        next.capacitorMounting = String(value);
        break;
      case "capacitorTolerance":
        next.capacitorTolerance = String(value);
        break;
      case "capacitorCaseSize":
        next.capacitorCaseSize = String(value);
        break;
      case "capacitorEsrMax":
        next.capacitorEsrMax = String(value);
        break;
      case "capacitorRippleMin":
        next.capacitorRippleMin = String(value);
        break;
      case "capacitorLifetimeMin":
        next.capacitorLifetimeMin = String(value);
        break;
      case "capacitorTemperatureRange":
        next.capacitorTemperatureRange = String(value);
        break;
      case "capacitorEnergyMin":
        next.capacitorEnergyMin = String(value);
        break;
      case "genericInterface":
        next.genericInterface = String(value);
        break;
      case "application":
        next.application = String(value);
        if (next.application !== "asset tracking") next.positioning = undefined;
        break;
      case "specialRequirements": {
        const values = Array.isArray(value) ? value.map(String) : [String(value)];

        if (next.catalogCategory === "Capacitors") {
          const detail = values.join(" ");
          const inferredCap = inferFromText(`capacitor ${detail}`);
          if (inferredCap.capacitorCaseSize) next.capacitorCaseSize = inferredCap.capacitorCaseSize;
          if (inferredCap.capacitorEsrMax) next.capacitorEsrMax = inferredCap.capacitorEsrMax;
          if (inferredCap.capacitorRippleMin) next.capacitorRippleMin = inferredCap.capacitorRippleMin;
          if (inferredCap.capacitorLifetimeMin) next.capacitorLifetimeMin = inferredCap.capacitorLifetimeMin;
          if (inferredCap.capacitorTemperatureRange) next.capacitorTemperatureRange = inferredCap.capacitorTemperatureRange;
          if (inferredCap.capacitorEnergyMin) next.capacitorEnergyMin = inferredCap.capacitorEnergyMin;
        }
        const noSpecial = values.some((v) => /no special/i.test(v));
        next.specialRequirements = noSpecial ? "No special requirements" : values.join(" + ");
        if (values.some((v) => /battery|low power/i.test(v))) {
          next.lowPower = true;
        } else if (next.application === "asset tracking") {
          next.lowPower = undefined;
        } else {
          next.lowPower = undefined;
        }
        break;
      }
      case "supportRequested":
        next.supportRequested = Boolean(value);
        break;
      case "supportGoal":
        next.supportGoal = String(value);
        next.supportRequested = next.supportGoal !== "none";
        if (next.supportGoal !== "technical") {
          next.supportTopic = undefined;
        }
        if (next.supportGoal !== "commercial") {
          next.targetVolume = undefined;
          next.projectTimeline = undefined;
        }
        if (next.supportGoal === "none") {
          next.supportProduct = undefined;
          next.supportTopic = undefined;
          next.targetVolume = undefined;
          next.projectTimeline = undefined;
        }
        break;
      case "supportProduct":
        next.supportProduct = String(value);
        break;
      case "supportTopic":
        next.supportTopic = String(value);
        break;
      case "designSituation":
        next.designSituation = String(value);
        if (next.designSituation !== "Replacement / redesign") {
          next.existingComponent = undefined;
        }
        break;
      case "existingComponent":
        next.existingComponent = String(value);
        break;
      case "targetVolume":
        next.targetVolume = String(value);
        break;
      case "projectTimeline":
        next.projectTimeline = String(value);
        break;
      case "projectPartners": {
        const values = Array.isArray(value) ? value.map(String) : [String(value)];
        next.projectPartners = values.some((v) => /none yet/i.test(v))
          ? "None yet"
          : values.join(" + ");
        break;
      }
      case "technologies": {
        next.technologies = [
          ...new Set(Array.isArray(value) ? value.map(String) : [String(value)]),
        ];

        if (!next.technologies.includes("cellular")) {
          next.cellularClass = undefined;
          next.region = undefined;
        }
        if (!next.technologies.includes("wifi")) {
          next.wifiGeneration = undefined;
          next.hostInterface = undefined;
        }
        if (!next.technologies.includes("bluetooth")) {
          next.bluetoothRequirement = undefined;
        }
        if (!next.technologies.includes("wifi") && !next.technologies.includes("bluetooth")) {
          next.architecture = undefined;
          next.antenna = undefined;
          next.antennaConnector = undefined;
          next.antennaCount = undefined;
        }
        if (!next.technologies.includes("gnss")) {
          next.gnssPrecision = undefined;
          next.gnssDualBand = undefined;
        }
        break;
      }
      case "positioning":
        next.positioning = value === "yes" ? "yes" : "no";
        if (next.positioning === "yes") {
          next.technologies = [...new Set([...(next.technologies ?? []), "gnss"])];
        }
        break;
      case "lowPower":
        next.lowPower = Boolean(value);
        break;
      case "cellularClass":
        next.cellularClass = String(value);
        break;
      case "region":
        next.region = String(value);
        break;
      case "architecture":
        next.architecture = String(value);
        break;
      case "antenna":
        next.antenna = String(value);
        break;
      case "wifiGeneration":
        next.wifiGeneration = Array.isArray(value) ? value.map(String) : [String(value)];
        break;
      case "gnssPrecision":
        next.gnssPrecision = String(value);
        break;
      case "hostInterface":
        next.hostInterface = String(value);
        break;
      case "antennaConnector":
        next.antennaConnector = String(value);
        break;
      case "antennaCount":
        next.antennaCount = String(value);
        break;
      case "antennaApplication":
        next.antennaApplication = String(value);
        next.antennaBand = undefined;
        next.antennaActive = undefined;
        break;
      case "antennaGnssBand":
      case "antennaWifiBand":
        next.antennaBand = String(value);
        break;
      case "antennaActive":
        next.antennaActive = String(value);
        break;
      case "bluetoothRequirement":
        next.bluetoothRequirement = String(value);
        if (String(value) !== "No requirement") {
          next.technologies = [...new Set([...(next.technologies ?? []), "bluetooth"])];
        }
        break;
      case "maxFootprint":
        next.maxFootprint = String(value);
        break;
      case "formFactor":
        next.formFactor = String(value);
        break;
      case "gnssDualBand":
        next.gnssDualBand = String(value);
        break;
    }

    setRequirements(next);
    addMessage("bot", localizedNaturalReply(key, value, language));
    setQuickOptions([]);
    setMultiSelected([]);
    setActiveQuestion(null);

    if (isCommercialKey(key)) {
      if (key === "supportGoal" && String(value) === "none") {
        setFinished(true);
      }
      window.setTimeout(() => askCommercialNext(next), 60);
    } else {
      // Every technical answer goes back through the adaptive engine.
      // If another useful requirement can separate the remaining candidates,
      // ask it; otherwise askNext() starts matching automatically.
      window.setTimeout(() => void askNext(next), 60);
    }
  }

  function submitText() {
    const q = input.trim();
    if (!q || !activeQuestion) return;
    setInput("");

    if (activeQuestion === "initialNeed") {
      applyAnswer("initialNeed", q, q);
      return;
    }

    if (activeQuestion.startsWith("engineering:")) {
      if (/no preference|not sure|open|egal|keine präferenz|keine praeferenz/i.test(q)) {
        return applyAnswer(activeQuestion, "__open__", q);
      }
      return applyAnswer(activeQuestion, q, q);
    }

    const inferred = inferFromText(q);

    if (activeQuestion === "productDomain") {
      const d = inferred.productDomain;
      if (d) return applyAnswer(activeQuestion, d, q);
    }
    if (activeQuestion === "catalogCategory") {
      if (inferred.catalogCategory) return applyAnswer(activeQuestion, inferred.catalogCategory, q);
      return applyAnswer(activeQuestion, q, q);
    }
    if (activeQuestion === "genericInterface") {
      if (inferred.genericInterface) return applyAnswer(activeQuestion, inferred.genericInterface, q);
      if (/no preference|not sure/i.test(q)) return applyAnswer(activeQuestion, "No preference", q);
    }
    if (activeQuestion === "capacitorCapacitance") {
      const c = parseCapacitanceUf(q);
      if (c != null) return applyAnswer(activeQuestion, formatCapacitanceUf(c), q);
    }
    if (activeQuestion === "capacitorVoltage") {
      const v = parseSimpleNumber(q);
      if (v != null && v > 0) return applyAnswer(activeQuestion, `${v} V`, q);
    }
    if (activeQuestion === "capacitorTechnology") {
      const tech = capacitorTechnologyFromText(q);
      if (tech) return applyAnswer(activeQuestion, tech, q);
      if (/no preference|not sure|any|egal|keine präferenz|keine praeferenz/i.test(q))
        return applyAnswer(activeQuestion, "No preference", q);
    }
    if (activeQuestion === "capacitorMounting") {
      if (/through[- ]?hole|tht|radial|axial|leaded|bedrahtet/i.test(q))
        return applyAnswer(activeQuestion, "Through-hole", q);
      if (/smd|smt|surface[- ]?mount/i.test(q))
        return applyAnswer(activeQuestion, "SMD", q);
      if (/no preference|not sure|any|egal|keine präferenz|keine praeferenz/i.test(q))
        return applyAnswer(activeQuestion, "No preference", q);
    }
    if (activeQuestion === "capacitorTolerance") {
      const tol = q.match(/(?:±|\+\/-|\+-)?\s*(\d+(?:[.,]\d+)?)\s*%/);
      if (tol) return applyAnswer(activeQuestion, `±${Number(tol[1].replace(",", "."))}%`, q);
      if (/no preference|not sure|any|egal|keine präferenz|keine praeferenz/i.test(q))
        return applyAnswer(activeQuestion, "No preference", q);
    }

    if (activeQuestion === "supportGoal") {
      if (/technical|fae|engineer|technik|technisch/i.test(q)) return applyAnswer(activeQuestion, "technical", q);
      if (/price|pricing|availability|sample|quote|preis|verfügbarkeit|verfuegbarkeit|muster/i.test(q))
        return applyAnswer(activeQuestion, "commercial", q);
      if (/^(no|n|nein)|enough|not now|reicht|nicht jetzt/i.test(q))
        return applyAnswer(activeQuestion, "none", q);
    }
    if (activeQuestion === "supportProduct") return applyAnswer(activeQuestion, q, q);
    if (activeQuestion === "supportTopic") return applyAnswer(activeQuestion, q, q);
    if (activeQuestion === "designSituation") {
      if (/replacement|replace|redesign|existing|ersetzen|ersatz|bestehend/i.test(q)) return applyAnswer(activeQuestion, "Replacement / redesign", q);
      if (/new design|new project|new|neues design|neues projekt/i.test(q)) return applyAnswer(activeQuestion, "New design", q);
      if (/not sure|unknown|noch offen|unsicher/i.test(q)) return applyAnswer(activeQuestion, "Not sure yet", q);
    }
    if (activeQuestion === "existingComponent") return applyAnswer(activeQuestion, q, q);

    if (activeQuestion === "application") return applyAnswer(activeQuestion, inferred.application ?? q, q);
    if (activeQuestion === "specialRequirements") return applyAnswer(activeQuestion, q, q);
    if (activeQuestion === "targetVolume") return applyAnswer(activeQuestion, q, q);
    if (activeQuestion === "projectTimeline") return applyAnswer(activeQuestion, q, q);
    if (activeQuestion === "projectPartners") return applyAnswer(activeQuestion, q, q);
    if (activeQuestion === "technologies" && inferred.technologies?.length)
      return applyAnswer(activeQuestion, inferred.technologies, q);
    if (activeQuestion === "cellularClass" && inferred.cellularClass)
      return applyAnswer(activeQuestion, inferred.cellularClass, q);
    if (activeQuestion === "region" && inferred.region) return applyAnswer(activeQuestion, inferred.region, q);
    if (activeQuestion === "architecture" && inferred.architecture)
      return applyAnswer(activeQuestion, inferred.architecture, q);
    if (activeQuestion === "antenna" && inferred.antenna) return applyAnswer(activeQuestion, inferred.antenna, q);
    if (activeQuestion === "wifiGeneration" && inferred.wifiGeneration)
      return applyAnswer(activeQuestion, inferred.wifiGeneration, q);
    if (activeQuestion === "gnssPrecision" && inferred.gnssPrecision)
      return applyAnswer(activeQuestion, inferred.gnssPrecision, q);
    if (
      activeQuestion === "gnssPrecision" &&
      /not sure|no preference|open|egal|keine präferenz|keine praeferenz|weiß nicht|weiss nicht/i.test(q)
    )
      return applyAnswer(activeQuestion, "No preference", q);

    if (activeQuestion === "positioning") {
      if (/^(yes|y|ja|gnss|gps)/i.test(q)) return applyAnswer(activeQuestion, "yes", q);
      if (/^(no|n|nein)/i.test(q)) return applyAnswer(activeQuestion, "no", q);
    }

    if (activeQuestion === "lowPower") {
      if (/^(yes|y|ja)|battery|low power|batterie|stromsparend/i.test(q)) return applyAnswer(activeQuestion, true, q);
      if (/^(no|n|nein)/i.test(q)) return applyAnswer(activeQuestion, false, q);
    }

    if (activeQuestion === "hostInterface") {
      if (/\bsdio\b/i.test(q) && /\bpcie\b|pci express/i.test(q)) return applyAnswer(activeQuestion, "SDIO or PCIe", q);
      if (/\bsdio\b/i.test(q)) return applyAnswer(activeQuestion, "SDIO", q);
      if (/\bpcie\b|pci express/i.test(q)) return applyAnswer(activeQuestion, "PCIe", q);
      if (/no preference|not sure|either/i.test(q)) return applyAnswer(activeQuestion, "No preference", q);
    }

    if (activeQuestion === "antennaConnector") {
      if (/u\.?fl|ufl/i.test(q)) return applyAnswer(activeQuestion, "U.FL", q);
      if (/pin|solder pad/i.test(q)) return applyAnswer(activeQuestion, "Antenna pin / solder pad", q);
      if (/no preference|not sure/i.test(q)) return applyAnswer(activeQuestion, "No preference", q);
    }

    if (activeQuestion === "antennaCount") {
      if (/\b2\b/.test(q)) return applyAnswer(activeQuestion, "2", q);
      if (/\b3\b/.test(q)) return applyAnswer(activeQuestion, "3", q);
      if (/no preference|not sure/i.test(q)) return applyAnswer(activeQuestion, "No preference", q);
    }

    if (activeQuestion === "antennaApplication") {
      if (/gnss|gps|galileo|glonass|beidou/i.test(q)) return applyAnswer(activeQuestion, "gnss", q);
      if (/wi-?fi|wlan|bluetooth|ble/i.test(q)) return applyAnswer(activeQuestion, "wifi_bt", q);
      if (/cellular|lte|5g|4g|gsm|umts|nb-?iot|lte-?m/i.test(q)) return applyAnswer(activeQuestion, "cellular", q);
      if (/lora|sigfox|ism|433|868|915|sub[- ]?ghz/i.test(q)) return applyAnswer(activeQuestion, "ism", q);
      if (/multi|combination|combined/i.test(q)) return applyAnswer(activeQuestion, "multi", q);
    }

    if (activeQuestion === "antennaGnssBand") {
      if (/l2|l5|dual|multi/i.test(q)) return applyAnswer(activeQuestion, "gnss_multiband", q);
      if (/\bl1\b/i.test(q)) return applyAnswer(activeQuestion, "gnss_l1", q);
      if (/no preference|not sure|open/i.test(q)) return applyAnswer(activeQuestion, "No preference", q);
    }

    if (activeQuestion === "antennaWifiBand") {
      if (/6e|6\s*ghz/i.test(q)) return applyAnswer(activeQuestion, "wifi_6e", q);
      if (/2[.,]4.*5|dual/i.test(q)) return applyAnswer(activeQuestion, "wifi_245", q);
      if (/2[.,]4/i.test(q)) return applyAnswer(activeQuestion, "wifi_24", q);
      if (/no preference|not sure|open/i.test(q)) return applyAnswer(activeQuestion, "No preference", q);
    }

    if (activeQuestion === "antennaActive") {
      if (/\bactive\b|aktiv/i.test(q)) return applyAnswer(activeQuestion, "active", q);
      if (/\bpassive\b|passiv/i.test(q)) return applyAnswer(activeQuestion, "passive", q);
      if (/no preference|not sure|open/i.test(q)) return applyAnswer(activeQuestion, "No preference", q);
    }

    if (activeQuestion === "bluetoothRequirement") {
      const m = q.match(/(?:bluetooth|ble|bt)?\s*([4-6](?:\.\d+)?)/i);
      if (m) return applyAnswer(activeQuestion, `Bluetooth ${m[1]}+`, q);
      if (/required|yes/i.test(q)) return applyAnswer(activeQuestion, "Bluetooth required, version open", q);
      if (/no|not required|no preference/i.test(q)) return applyAnswer(activeQuestion, "No requirement", q);
    }

    if (activeQuestion === "maxFootprint") {
      const m = q.match(/(\d+(?:\.\d+)?)\s*mm(?:2|²)?/i);
      if (m) return applyAnswer(activeQuestion, `≤ ${m[1]} mm²`, q);
      if (/no fixed|no limit|not sure/i.test(q)) return applyAnswer(activeQuestion, "No fixed limit", q);
    }

    if (activeQuestion === "formFactor") {
      if (/mini\s*pcie/i.test(q)) return applyAnswer(activeQuestion, "Mini PCIe", q);
      if (/\blga\b/i.test(q)) return applyAnswer(activeQuestion, "LGA", q);
      if (/\bm\.?2\b/i.test(q)) return applyAnswer(activeQuestion, "M.2", q);
      if (/no preference|not sure/i.test(q)) return applyAnswer(activeQuestion, "No preference", q);
    }

    if (activeQuestion === "gnssDualBand") {
      if (/l1\s*\+\s*l5|dual[- ]band/i.test(q))
        return applyAnswer(activeQuestion, "L1 + L5 required", q);
      if (/l1 only|l1 is sufficient|single[- ]band/i.test(q))
        return applyAnswer(activeQuestion, "L1 sufficient", q);
      if (/not sure|no preference|open|egal|keine präferenz|keine praeferenz/i.test(q))
        return applyAnswer(activeQuestion, "No preference", q);
    }

    addMessage(
      "bot",
      tr(
        language,
        "I’m not fully sure how to map that answer to this requirement. Please choose one of the options below, or describe it a little more specifically.",
        "Ich kann diese Antwort noch nicht eindeutig der Anforderung zuordnen. Bitte wählen Sie eine der Optionen aus oder beschreiben Sie die Anforderung etwas genauer."
      )
    );
  }


  function selectedLabelsForEdit(key: QuestionKey, options: Option[]): string[] {
    const current = requirements[key as keyof Requirements];

    if (key === "technologies") {
      const tech = new Set(requirements.technologies ?? []);
      return options
        .filter((option) => {
          const values = Array.isArray(option.value) ? option.value.map(String) : [String(option.value)];
          return values.some((value) => tech.has(value));
        })
        .map((option) => option.label);
    }

    if (key === "wifiGeneration") {
      const generations = new Set(requirements.wifiGeneration ?? []);
      return options
        .filter((option) => generations.has(String(option.value)))
        .map((option) => option.label);
    }

    if (key === "specialRequirements" || key === "projectPartners") {
      const text = String(current ?? "");
      return options
        .filter((option) => text.split(" + ").includes(String(option.value)))
        .map((option) => option.label);
    }

    return [];
  }

  function editRequirement(rawKey: string) {
    if (rawKey.startsWith("engineering:")) {
      const field = rawKey.slice("engineering:".length);
      setFinished(false);
      setShowAllResults(false);
      setActiveQuestion(rawKey as QuestionKey);
      setQuickOptions([]);
      setMultiSelected([]);
      addMessage(
        "bot",
        tr(
          language,
          `Editing <strong>${htmlEscape(engineeringRequirementLabel(field, language))}</strong>. Enter the new requirement, or type <strong>No preference</strong> to leave it open.`,
          `Bearbeiten: <strong>${htmlEscape(engineeringRequirementLabel(field, language))}</strong>. Geben Sie die neue Anforderung ein oder <strong>Keine Präferenz</strong>, um sie offen zu lassen.`
        )
      );
      return;
    }

    const mappedKey =
      rawKey === "antennaBand"
        ? (requirements.antennaApplication === "gnss" ? "antennaGnssBand" : "antennaWifiBand")
        : rawKey;
    const key = mappedKey as QuestionKey;

    if (key === "existingComponent") {
      setFinished(false);
      setShowAllResults(false);
      setActiveQuestion(key);
      setQuickOptions([]);
      setMultiSelected([]);
      addMessage(
        "bot",
        tr(
          language,
          "Editing <strong>Existing component</strong>. Which existing component or part number are you replacing?",
          "Bearbeiten: <strong>Bestehende Komponente</strong>. Welche Komponente bzw. Teilenummer soll ersetzt werden?"
        )
      );
      return;
    }

    const rawQuestion = editableQuestionFor(key, requirements, matches);
    const q = localizeQuestion(
      rawQuestion ? { key, text: rawQuestion.text, options: rawQuestion.options } : null,
      language
    );
    if (!q) return;

    setFinished(false);
    setShowAllResults(false);
    setActiveQuestion(key);
    const editOptions = q.options ?? [];
    setQuickOptions(editOptions);
    setMultiSelected(isMultiSelectKey(key) ? selectedLabelsForEdit(key, editOptions) : []);
    addMessage(
      "bot",
      language === "de"
        ? `Bearbeiten: <strong>${htmlEscape(requirementLabel(key, language))}</strong>. ${q.text}`
        : `Editing <strong>${htmlEscape(requirementLabel(key, language))}</strong>. ${q.text}`
    );
  }

  const matchGroups = useMemo(
    () => groupMatchesByVerifiedFamily(matches),
    [matches]
  );

  const handoffOnlyKeys = new Set([
    "supportRequested",
    "supportGoal",
    "supportProduct",
    "supportTopic",
    "designSituation",
    "existingComponent",
    "targetVolume",
    "projectTimeline",
    "projectPartners",
  ]);

  const visibleRequirements = [
    ...Object.entries(requirements).filter(
      ([key, value]) =>
        key !== "initialNeed" &&
        key !== "newProject" &&
        key !== "engineering" &&
        key !== "answeredEngineering" &&
        !handoffOnlyKeys.has(key) &&
        value !== undefined &&
        value !== null &&
        value !== ""
    ),
    ...Object.entries(requirements.engineering ?? {}).map(
      ([key, value]) => [`engineering:${key}`, value] as [string, string | number | boolean]
    ),
  ];

  return (
    <div className="appShell">
      {matching && (
        <div
          className="matchingOverlay"
          role="status"
          aria-live="assertive"
          aria-label={tr(language, "Searching for new results", "Suche nach neuen Ergebnissen")}
        >
          <div className="matchingOverlayCard">
            <div className="matchingHeroIcon" aria-hidden="true">
              <span className="matchingSpinner matchingSpinnerHero" />
              <svg viewBox="0 0 24 24" focusable="false">
                <circle cx="10.5" cy="10.5" r="5.2" />
                <path d="M14.4 14.4L19.2 19.2" />
              </svg>
            </div>
            <strong>
              {tr(language, "Searching for new results…", "Suche nach neuen Ergebnissen…")}
            </strong>
            <span>
              {tr(
                language,
                "Please wait while your requirements are compared with the SE product database.",
                "Bitte warten Sie, während Ihre Anforderungen mit der SE-Produktdatenbank verglichen werden."
              )}
            </span>
          </div>
        </div>
      )}
      <header className="topbar">
        <div className="brand">
          <img src="/se-logo.png" alt="SE Spezial-Electronic" className="seLogo" />
          <div>
            <strong>{tr(language, "Intelligent Product Assistant", "Intelligenter Produktassistent")}</strong>
            <span>{tr(language, "FAE-guided product selection", "FAE-gestützte Produktauswahl")}</span>
          </div>
        </div>

        <div className="topStatus">
          <div className="languageSwitch" aria-label="Language">
            <button className={language === "en" ? "active" : ""} onClick={() => switchLanguage("en")}>EN</button>
            <button className={language === "de" ? "active" : ""} onClick={() => switchLanguage("de")}>DE</button>
          </div>

          {developerModeAvailable && (
            <div className="modeSwitch" aria-label="View mode">
              <button className={viewMode === "customer" ? "active" : ""} onClick={() => setViewMode("customer")}>
                {tr(language, "Customer", "Kunde")}
              </button>
              <button className={viewMode === "developer" ? "active" : ""} onClick={() => setViewMode("developer")}>
                Developer
              </button>
            </div>
          )}

          {developerModeAvailable && viewMode === "developer" && (
            <>
              {catalogStatus && (
                <div className="catalogBadge">
                  {catalogStatus.total_products} products · {catalogStatus.structured_products} structured · {catalogStatus.live_imported_products} live
                </div>
              )}
              <div className={`backend ${backend}`}>
                <span className="statusDot" />
                {backend === "connected" ? "Backend connected" : backend === "checking" ? "Checking backend…" : "Backend not reachable"}
              </div>
            </>
          )}
        </div>
      </header>

      <main className="page">
        <section className="hero">
          <h1 className="assistantTitle">SE PRODUCT ASSISTANT</h1>
          <button className="restart" onClick={reset}>↻ {tr(language, "Restart conversation", "Konversation neu starten")}</button>
        </section>

        <div className="workspace">
          <section className="leftPanel">
            <div className="panelHeader">
              <div>
                <h2>{tr(language, "Your requirements", "Ihre Anforderungen")}</h2>
                {viewMode === "developer" && (
                  <p>{tr(language, "The technical profile updates automatically as the conversation progresses.", "Das technische Profil wird während der Konversation automatisch aktualisiert.")}</p>
                )}
              </div>
              {viewMode === "developer" && (
                <div className="completionBadge">{completeness}% technical profile</div>
              )}
            </div>

            {viewMode === "developer" && (
              <div className="progressTrack">
                <div className="progressFill" style={{ width: `${completeness}%` }} />
              </div>
            )}

            <div className="requirements">
              {visibleRequirements.length ? (
                visibleRequirements.map(([key, value]) => (
                  <div className="requirement" key={key}>
                    <div className="requirementHead">
                      <span>{requirementLabel(key, language)}</span>
                      <button
                        type="button"
                        className="editRequirement"
                        onClick={() => editRequirement(key)}
                        disabled={matching}
                        aria-label={`${tr(language, "Edit", "Bearbeiten")} ${requirementLabel(key, language)}`}
                      >
                        {tr(language, "Edit", "Bearbeiten")}
                      </button>
                    </div>
                    <strong>
                      {key.startsWith("engineering:")
                        ? formatEngineeringRequirementValue(key.slice("engineering:".length), value)
                        : localizeValue(value, language)}
                    </strong>
                  </div>
                ))
              ) : (
                <div className="emptyState">
                  {tr(language, "Your requirements will appear here as you answer the questions.", "Ihre Anforderungen erscheinen hier, während Sie die Fragen beantworten.")}
                </div>
              )}
            </div>

            <div className="resultsHeader">
              <div>
                <h3>{tr(language, "Matching results", "Passende Produkte")}</h3>
                <span className={matching ? "matchingStatus" : undefined} aria-live="polite">
                  {matching ? (
                    <>
                      <span className="matchingSpinner matchingSpinnerSmall" aria-hidden="true" />
                      {tr(language, "Searching for new results…", "Suche nach neuen Ergebnissen…")}
                    </>
                  ) : matchGroups.length > 3 && !showAllResults ? (
                    tr(
                      language,
                      `${matches.length} matching SKUs · ${matchGroups.length} solution groups · showing top 3`,
                      `${matches.length} passende SKUs · ${matchGroups.length} Lösungsgruppen · Top 3 angezeigt`
                    )
                  ) : (
                    tr(
                      language,
                      `${matches.length} matching SKUs · ${matchGroups.length} solution groups`,
                      `${matches.length} passende SKUs · ${matchGroups.length} Lösungsgruppen`
                    )
                  )}
                </span>
              </div>
            </div>

            <div className={`results${matching && matches.length ? " resultsRefreshing" : ""}`}>
              {matches.length ? (
                (showAllResults ? matchGroups : matchGroups.slice(0, 3)).map((group, index) => {
                  const match = group.primary;
                  const bestPrimary = matchGroups[0]?.primary;
                  const topTechnicalTieCount = bestPrimary
                    ? matchGroups.filter((candidate) =>
                        candidate.primary.match_percent === bestPrimary.match_percent &&
                        candidate.primary.solution_scope_score === bestPrimary.solution_scope_score
                      ).length
                    : 0;
                  const isTopTechnicalTie = Boolean(
                    bestPrimary &&
                    topTechnicalTieCount > 1 &&
                    match.match_percent === bestPrimary.match_percent &&
                    match.solution_scope_score === bestPrimary.solution_scope_score
                  );
                  return (
                  <article
                    className="productCard"
                    key={group.key}
                    ref={index === 0 ? firstRecommendationRef : undefined}
                  >
                    <div className="productTop">
                      <div>
                        <div className="rank">
                          {isTopTechnicalTie
                            ? tr(language, "Top technical match · tied", "Technischer Top-Treffer · gleichauf")
                            : `#${index + 1} ${tr(language, "recommendation", "Empfehlung")}`}
                        </div>
                        <h3>{match.product.part_number}</h3>
                        <div className="productMeta">
                          {match.product.manufacturer} · {match.product.category}
                        </div>
                        {match.family && match.family.verification_status === "verified" && (
                          <div className="familyBadge">
                            <span>{tr(language, "Product family", "Produktfamilie")}</span>
                            <strong>{match.family.name}</strong>
                            <small>
                              {tr(
                                language,
                                "explicitly verified relationship",
                                "explizit verifizierte Zuordnung"
                              )}
                            </small>
                          </div>
                        )}
                      </div>
                      <div className="scoreStack customerScoreStack">
                        <div className="score">{match.match_percent}% {tr(language, "technical match", "technische Übereinstimmung")}</div>
                        <div className={`fitConfidence ${recommendationConfidenceClass(match)}`}>
                          {recommendationConfidenceLabel(match, language)}
                        </div>
                        {match.verification_required && match.verification_issues.length > 0 && (
                          <div className="fitIssue">
                            {verificationIssueText(match, language)}
                          </div>
                        )}
                        {match.extra_technologies.length === 0 ? (
                          <div className="scopeBadge scopeFocused">
                            {tr(language, "Focused", "Fokussiert")}
                          </div>
                        ) : (
                          <div className="scopeBadge">
                            {tr(
                              language,
                              `Includes ${match.extra_technologies.map((t) => t.toUpperCase()).join(", ")}`,
                              `Enthält zusätzlich ${match.extra_technologies.map((t) => t.toUpperCase()).join(", ")}`
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {viewMode === "developer" && (
                      <div className="developerEvidence">
                        Confidence {match.recommendation_confidence} · Scope {match.solution_scope_score}% · Evidence {match.evidence_score}% · {match.evidence_summary.verified} verified · {match.evidence_summary.inferred} inferred · {match.evidence_summary.not_verified} unknown · {match.evidence_summary.conflicting} conflicts
                      </div>
                    )}

                    <p>{match.product.description}</p>

                    <div className="tags">
                      {match.product.tags.slice(0, 7).map((tag) => (
                        <span key={tag}>{tag}</span>
                      ))}
                    </div>

                    {match.product.features && (
                      <div className="featureStrip">
                        {match.product.features.cellular_class && <span>{match.product.features.cellular_class}</span>}
                        {match.product.features.region && <span>{match.product.features.region}</span>}
                        {match.product.features.gnss_precision && <span>GNSS: {match.product.features.gnss_precision}</span>}
                        {match.product.features.wifi_generation && <span>Wi-Fi {match.product.features.wifi_generation}</span>}
                        {match.product.features.form_factor && <span>{match.product.features.form_factor}</span>}
                        {match.product.features.antenna_applications?.length ? (
                          <span>
                            {match.product.features.antenna_applications.map((value) =>
                              value === "gnss" ? "GNSS" :
                              value === "wifi_bt" ? "Wi-Fi / Bluetooth" :
                              value === "cellular" ? "Cellular" :
                              value === "ism" ? "ISM / LPWAN" : value
                            ).join(" + ")}
                          </span>
                        ) : null}
                        {match.product.features.antenna_bands?.length ? (
                          <span>
                            {match.product.features.antenna_bands.includes("gnss_multiband") ? "GNSS multi-band" :
                             match.product.features.antenna_bands.includes("gnss_l1") ? "GNSS L1" :
                             match.product.features.antenna_bands.includes("wifi_6e") ? "Wi-Fi 6E / 6 GHz" :
                             match.product.features.antenna_bands.includes("wifi_245") ? "2.4 + 5 GHz" :
                             match.product.features.antenna_bands.includes("wifi_24") ? "2.4 GHz" : ""}
                          </span>
                        ) : null}
                        {match.product.features.antenna_active === true && <span>Active antenna</span>}
                        {match.product.features.antenna_active === false && <span>Passive antenna</span>}
                        {match.product.features.capacitance_uf != null && (
                          <span>C: {formatCapacitanceUf(match.product.features.capacitance_uf)}</span>
                        )}
                        {match.product.features.capacitor_voltage_v != null && (
                          <span>{match.product.features.capacitor_voltage_v} V</span>
                        )}
                        {match.product.features.capacitor_tolerance_pct != null && (
                          <span>±{match.product.features.capacitor_tolerance_pct}%</span>
                        )}
                        {match.product.features.capacitor_technology && (
                          <span>{match.product.features.capacitor_technology}</span>
                        )}
                        {match.product.features.capacitor_mounting && (
                          <span>{match.product.features.capacitor_mounting}</span>
                        )}
                        {match.product.features.capacitor_case_size && (
                          <span>{match.product.features.capacitor_case_size}</span>
                        )}
                        {match.product.features.temperature_min != null && match.product.features.temperature_max != null && (
                          <span>{match.product.features.temperature_min}…+{match.product.features.temperature_max} °C</span>
                        )}
                        {match.product.features.imported_live && <span className="liveFeature">Live SE catalog</span>}
                      </div>
                    )}

                    <div className="reasonBox">
                      <strong>{tr(language, "Why it matches", "Warum es passt")}</strong>
                      {match.reasons.length ? (
                        <ul>
                          {match.reasons.map((reason) => <li key={reason}>{localizeReason(reason, language)}</li>)}
                        </ul>
                      ) : (
                        <p>{tr(language, "Basic catalog fit.", "Grundlegende Übereinstimmung mit den Katalogdaten.")}</p>
                      )}
                    </div>

                    <details className="technicalDetails">
                      <summary>
                        <span>{tr(language, "Technical details", "Technische Details")}</span>
                        <span className="technicalDetailsHint">{tr(language, "Sources & specification checks", "Quellen & Spezifikationsprüfung")}</span>
                      </summary>

                      <div className="technicalDetailsContent">
                        {!!match.criterion_evidence.length ? (
                          <div className="criterionEvidenceList customerEvidenceList">
                            {match.criterion_evidence.map((item) => {
                              const sourceLabel = evidenceSourceLabel(item);
                              const positive = item.status === "verified" || item.status === "inferred";
                              return (
                                <div className={`criterionEvidence ${item.status}`} key={item.key}>
                                  <span className="evidenceIcon" aria-hidden="true">
                                    {evidenceStatusIcon(item.status)}
                                  </span>
                                  <div className="criterionEvidenceBody">
                                    <div className="criterionEvidenceTop">
                                      <strong>{item.label}</strong>
                                      <span>{customerCriterionLabel(item, language)}</span>
                                    </div>

                                    {item.evidence_value && (
                                      <div className="evidenceValue">
                                        {tr(language, "Technical value", "Technischer Wert")}: {item.evidence_value}
                                      </div>
                                    )}

                                    {sourceLabel && (
                                      item.source_url ? (
                                        <a
                                          className="evidenceSource"
                                          href={item.source_url}
                                          target="_blank"
                                          rel="noreferrer"
                                        >
                                          {tr(language, "Source", "Quelle")}: {sourceLabel}
                                        </a>
                                      ) : (
                                        <div className="evidenceSource">
                                          {tr(language, "Source", "Quelle")}: {sourceLabel}
                                        </div>
                                      )
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <p className="technicalDetailsEmpty">
                            {tr(language, "Technical source details are not available for the current criteria.", "Für die aktuellen Kriterien sind noch keine technischen Quelldetails verfügbar.")}
                          </p>
                        )}

                        {(match.evidence_summary.not_verified > 0 || match.evidence_summary.conflicting > 0) && (
                          <div className="technicalReviewNote">
                            {tr(
                              language,
                              "Some specifications may require final confirmation before design-in. An SE FAE can verify these details if they are critical to your project.",
                              "Einige Spezifikationen sollten vor dem Design-in abschließend bestätigt werden. Ein SE FAE kann kritische Projektdetails prüfen."
                            )}
                          </div>
                        )}
                      </div>
                    </details>

                    {group.variants.length > 1 && match.family && (
                      <details className="familyVariants">
                        <summary>
                          {tr(
                            language,
                            `${group.variants.length} matching SKUs in ${match.family.name}`,
                            `${group.variants.length} passende SKUs in ${match.family.name}`
                          )}
                        </summary>
                        <div className="familyVariantList">
                          {group.variants.map((variant) => (
                            <div className="familyVariantRow" key={variant.product.id}>
                              <div>
                                <strong>{variant.product.part_number}</strong>
                                <span>{variant.product.category}</span>
                              </div>
                              <b>{variant.match_percent}%</b>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}

                    <div className="commercial">
                      <span><b>{tr(language, "Lifecycle", "Lebenszyklus")}:</b> {match.product.lifecycle}</span>
                      <span><b>{tr(language, "Availability", "Verfügbarkeit")}:</b> {match.product.availability}</span>
                    </div>

                    <div className="cardActions">
                      {match.product.product_url && (
                        <a href={match.product.product_url} target="_blank" rel="noreferrer" className="primaryAction">
                          {tr(language, "View SE product", "SE-Produkt ansehen")}
                        </a>
                      )}
                      <a
                        href={`mailto:support@spezial.com?subject=${encodeURIComponent(
                          `Technical request: ${match.product.part_number}`
                        )}`}
                      >
                        {tr(language, "Ask an FAE", "FAE anfragen")}
                      </a>
                    </div>
                  </article>
                  );
                })
              ) : finished ? (
                <div className="emptyState">{tr(language, "No validated product match was found.", "Es wurde kein passendes validiertes Produkt gefunden.")}</div>
              ) : (
                <div className="emptyState">
                  {tr(language, "Answer the relevant technical questions and suitable SE products will appear here.", "Beantworten Sie die relevanten technischen Fragen; passende SE-Produkte erscheinen anschließend hier.")}
                </div>
              )}
              {matchGroups.length > 3 && (
                <button className="showMoreResults" onClick={() => setShowAllResults((v) => !v)}>
                  {showAllResults
                    ? tr(language, "Show top 3 only", "Nur Top 3 anzeigen")
                    : tr(
                        language,
                        `Show all ${matchGroups.length} solution groups`,
                        `Alle ${matchGroups.length} Lösungsgruppen anzeigen`
                      )}
                </button>
              )}
            </div>
          </section>

          <aside className="chatPanel">
            <div className="chatHeader">
              <div>
                <span className="chatOnline" />
                <div>
                  <strong>SE Product Assistant</strong>
                  <span>{tr(language, "Online · technical selection", "Online · technische Produktauswahl")}</span>
                </div>
              </div>
              <button onClick={reset}>{tr(language, "Restart", "Neu starten")}</button>
            </div>

            <div className="chatBody" ref={chatBodyRef}>
              {messages.map((message) => (
                <div className={`message ${message.role}`} key={message.id}>
                  <div className="bubble" dangerouslySetInnerHTML={{ __html: message.html }} />
                </div>
              ))}

              {!!quickOptions.length && (
                <div className="quickOptionsWrap">
                  <div className={`quickOptions ${isMultiSelectKey(activeQuestion) ? "multiChoice" : ""}`}>
                    {quickOptions.map((option) => {
                      const selected = multiSelected.includes(option.label);
                      return (
                        <button
                          key={option.label}
                          className={selected ? "selectedOption" : ""}
                          aria-pressed={isMultiSelectKey(activeQuestion) ? selected : undefined}
                          onClick={() => {
                            if (!activeQuestion) return;
                            if (isMultiSelectKey(activeQuestion)) {
                              toggleMultiOption(option);
                            } else {
                              void applyAnswer(activeQuestion, option.value, option.label);
                            }
                          }}
                        >
                          {isMultiSelectKey(activeQuestion) && (
                            <span className="choiceMark" aria-hidden="true">{selected ? "✓" : "+"}</span>
                          )}
                          {option.label}
                        </button>
                      );
                    })}
                  </div>

                  {isMultiSelectKey(activeQuestion) && (
                    <div className="multiChoiceActions">
                      <span>{tr(language, "Select one or more options.", "Wählen Sie eine oder mehrere Optionen.")}</span>
                      <button
                        type="button"
                        className="confirmChoices"
                        disabled={!multiSelected.length}
                        onClick={confirmMultiSelection}
                      >
                        {tr(language, "Confirm choices", "Auswahl bestätigen")}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {finished && (
                <div className="quickOptions finalActions">
                  <button onClick={() => addMessage(
                    "bot",
                    tr(
                      language,
                      "You can restart the conversation for another requirement, or open one of the product pages on the left for more details.",
                      "Sie können die Konversation für eine weitere Anforderung neu starten oder links eine Produktseite für weitere Details öffnen."
                    )
                  )}>
                    {tr(language, "Continue", "Weiter")}
                  </button>
                  <button onClick={reset}>{tr(language, "Start another request", "Neue Anfrage starten")}</button>
                </div>
              )}

              <div />
            </div>

            <div className="chatInput">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitText()}
                placeholder={tr(language, "Describe what you need or type your answer…", "Beschreiben Sie Ihre Anforderung oder geben Sie Ihre Antwort ein…")}
                disabled={!activeQuestion || matching}
              />
              <button onClick={submitText} disabled={!input.trim() || !activeQuestion || matching}>
                {tr(language, "Send", "Senden")}
              </button>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}

export default App;
