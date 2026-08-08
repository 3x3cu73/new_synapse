// src/utils/constants.js

export const DEPARTMENTS = [
  "Applied Mechanics",
  "Biochemical Engineering and Biotechnology",
  "Chemical Engineering",
  "Chemistry",
  "Civil Engineering",
  "Computer Science and Engineering",
  "Design",
  "Electrical Engineering",
  "Energy Science and Engineering",
  "Humanities and Social Sciences",
  "Management Studies",
  "Materials Science and Engineering",
  "Mathematics",
  "Mechanical Engineering",
  "Physics",
  "Textile and Fibre Engineering"
];

export const HOSTELS = [
  "Aravali", "Dronagiri", "Girnar", "Himadri", "Jwalamukhi", "Kailash", "Karakoram", 
  "Kumaon", "Nalanda", "Nilgiri", "Satpura", "Sahyadri", "Saptagiri", "Shivalik", 
  "Udaigiri", "Vindhyachal", "Zanskar", "Dayscholar"
];


export const YEARS = [1, 2, 3, 4, 5];

// Org types (must match backend enums)

export const ORG_TYPES = [
  { label: "Club", value: "club" },
  { label: "Board", value: "board" },
  { label: "Society", value: "society" },
  { label: "Fest", value: "fest" },
  { label: "Sport", value: "sport" },
  { label: "Department", value: "department" }
];

// src/utils/constants.js

export const HEAD_ROLES = [
  "overall coordinator",
  "co overall coordinator",
  "caic admin",
  "president",
  "general secretary",
  "vice president",
  "deputy general secretary",
  "secretary",
  "convener"
];

export const TEAM_ROLES = [
  "team head",
  "achead",
  "coordinator",
  "executive"
];

export const ALL_ROLES = [...HEAD_ROLES, ...TEAM_ROLES];

// Master list of all organizations (Matches backend OrgName enum)
export const ALL_ORGS = {
  "club": [
    "devclub", "robotics club", "aeromodelling club", "business and consulting club", 
    "economics club", "physics and astronomy club", "algorithms and computing club", 
    "aries", "igem", "hyperloop club", "indian game theory society", "blockchain society",
    "axlr8r formula racing", "music club", "dance club", "dramatics club", 
    "literary club", "debating club", "photography and films club", 
    "fine arts and crafts club", "design club", "quizzing club", 
    "hindi samiti", "spic macay", "envogue", "indradhanu"
  ],
  "board": [
    "student affairs council", "board for hostel management", "board for student welfare",
    "board for sports activities", "board for recreational and creative activities", 
    "board for student publications", "co-curricular and academic interaction council"
  ],
  "society": [
    "mathsoc", "aces acm", "beta", "mses", "cef", "mes", "ches", "energy society",
    "physoc", "ees", "tes", "chemocronies"
  ],
  "fest": ["rendezvous", "tryst", "becon", "literati", "sportech"],
  "sport": [
    "aquatics", "athletics", "badminton", "basketball", "chess", "cricket",
    "football", "hockey", "lawn tennis", "squash", "table tennis", "volleyball", "weightlifting"
  ],
  "department": [
    "applied mechanics", "biochemical engineering and biotechnology", "chemical engineering",
    "chemistry", "civil engineering", "computer science and engineering", "design",
    "electrical engineering", "energy science and engineering", "humanities and social sciences",
    "management studies", "materials science and engineering", "mathematics",
    "mechanical engineering", "physics", "textile and fibre engineering"
  ]
};

// ─── GENRES / INTERESTS ────────────────────────────────
export const GENRES = [
  "AI & Machine Learning",
  "Web Development",
  "App Development",
  "Competitive Programming",
  "Cyber Security",
  "Blockchain & Web3",
  "Data Science",
  "Cloud Computing",
  "IoT",
  "Robotics",
  "Aeromodelling",
  "Electronics",
  "Astronomy",
  "Physics",
  "Mathematics",
  "Chemistry",
  "Biology & Biotech",
  "Economics & Finance",
  "Consulting",
  "Entrepreneurship",
  "Game Theory",
  "Music",
  "Dance",
  "Drama & Theatre",
  "Photography",
  "Film Making",
  "Fine Arts",
  "Design & UI/UX",
  "Fashion",
  "Literature & Poetry",
  "Debating",
  "Public Speaking",
  "Quizzing",
  "Hindi & Regional Languages",
  "Writing & Journalism",
  "Cricket",
  "Football",
  "Basketball",
  "Badminton",
  "Table Tennis",
  "Chess",
  "Athletics",
  "Swimming",
  "Volleyball",
  "Squash",
  "Hockey",
  "Weightlifting",
  "Yoga & Fitness",
  "Environment & Sustainability",
  "Social Service",
  "Mental Health & Wellness",
  "Gaming & Esports",
  "Open Source",
  "Research & Innovation",
];

// High-level genre categories for the home page
export const GENRE_CATEGORIES = [
  {
    name: "Tech",
    icon: "Monitor",
    color: "#8b5cf6",
    genres: ["AI & Machine Learning", "Web Development", "App Development", "Competitive Programming", "Cyber Security", "Blockchain & Web3", "Data Science", "Cloud Computing", "IoT", "Open Source"],
  },
  {
    name: "Science",
    icon: "FlaskConical",
    color: "#06b6d4",
    genres: ["Robotics", "Aeromodelling", "Electronics", "Astronomy", "Physics", "Mathematics", "Chemistry", "Biology & Biotech", "Research & Innovation"],
  },
  {
    name: "Music & Arts",
    icon: "Music",
    color: "#ec4899",
    genres: ["Music", "Dance", "Drama & Theatre", "Fine Arts", "Fashion"],
  },
  {
    name: "Media",
    icon: "Camera",
    color: "#f59e0b",
    genres: ["Photography", "Film Making", "Design & UI/UX", "Writing & Journalism"],
  },
  {
    name: "Literary",
    icon: "BookOpen",
    color: "#10b981",
    genres: ["Literature & Poetry", "Debating", "Public Speaking", "Quizzing", "Hindi & Regional Languages"],
  },
  {
    name: "Sports",
    icon: "Trophy",
    color: "#ef4444",
    genres: ["Cricket", "Football", "Basketball", "Badminton", "Table Tennis", "Chess", "Athletics", "Swimming", "Volleyball", "Squash", "Hockey", "Weightlifting", "Yoga & Fitness"],
  },
  {
    name: "Business",
    icon: "Briefcase",
    color: "#6366f1",
    genres: ["Economics & Finance", "Consulting", "Entrepreneurship", "Game Theory"],
  },
  {
    name: "Lifestyle",
    icon: "Leaf",
    color: "#14b8a6",
    genres: ["Environment & Sustainability", "Social Service", "Mental Health & Wellness", "Gaming & Esports"],
  },
];

export const LH_ROOMS = [
  "LH108","LH111","LH114","LH121",
  "LH308","LH310","LH313.1","LH313.2","LH313.3","LH313.4","LH313.5","LH316","LH318","LH325",
  "LH408","LH410","LH413.1","LH413.2","LH413.3","LH413.4","LH413.5","LH416","LH418","LH421","LH422",
  "LH510","LH512","LH517","LH518","LH519","LH520","LH521","LH526","LH527",
  "LH602","LH603","LH604","LH605","LH606","LH611","LH612","LH613","LH614","LH615","LH619","LH620","LH621","LH622","LH623",
  "LH-ATR",
];

export const isLhVenue = (venue) => {
  if (!venue) return false;
  return /^LH[\d\-.]/i.test(venue.trim());
};

/**
 * Detect if user is typing an LH-style venue and extract the numeric/id part.
 * Matches: lh5, LH 325, lh313.2, LH-ATR, lecture hall 5, lecture hall complex 3,
 * lhc 4, lhc325, Lecture Hall Complex 313.1, etc.
 * Returns { match: true, fragment: "325" } or { match: false }
 */
export const detectLhInput = (text) => {
  if (!text) return { match: false };
  const t = text.trim();
  // Pattern: (lh|lhc|lecture hall|lecture hall complex) + optional space + number/id part
  const re = /^(?:lecture\s*hall\s*(?:complex)?|lhc|lh)\s*[-.]?\s*(.*)$/i;
  const m = t.match(re);
  if (!m) return { match: false };
  const fragment = (m[1] || '').replace(/\s+/g, '').trim();
  return { match: true, fragment };
};

/**
 * Find the best matching LH room for a typed fragment.
 * e.g. "3" -> first room starting with 3 (LH308), "325" -> LH325, "atr" -> LH-ATR
 */
export const findLhRoom = (fragment) => {
  if (!fragment) return '';
  const f = fragment.toLowerCase();
  // Exact match first (fragment matches the part after "LH")
  const exact = LH_ROOMS.find(r => {
    const suffix = r.replace(/^LH[-.]?/i, '').toLowerCase();
    return suffix === f;
  });
  if (exact) return exact;
  // Prefix match
  const prefix = LH_ROOMS.find(r => {
    const suffix = r.replace(/^LH[-.]?/i, '').toLowerCase();
    return suffix.startsWith(f);
  });
  if (prefix) return prefix;
  // Contains match (for "atr" -> LH-ATR)
  return LH_ROOMS.find(r => r.toLowerCase().includes(f)) || '';
};