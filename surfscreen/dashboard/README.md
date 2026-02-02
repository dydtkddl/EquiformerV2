# SurfScreen Dashboard

Enterprise-grade React/Next.js web dashboard for the SurfScreen surface adsorption screening platform.

## ✨ Features

- **Real-time Job Monitoring** - Live status updates with automatic polling
- **Job Management** - Create, track, cancel, and download jobs
- **3D Structure Viewer** - Interactive molecular visualization with 3Dmol.js
- **Interactive Charts** - Energy and temperature plots with Recharts
- **Dark/Light Theme** - Persistent theme preference with system detection
- **Responsive Design** - Mobile-first design with desktop optimization

## 🚀 Getting Started

### Prerequisites

- Node.js 20+
- SurfScreen API server running

### Installation

```bash
# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local with your API URL and key
```

### Development

```bash
# Start development server
npm run dev

# Open http://localhost:3000
```

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

## 📁 Project Structure

```
src/
├── app/                 # Next.js App Router pages
│   ├── jobs/           # Job management pages
│   ├── screening/      # Screening workflow
│   ├── md/             # MD simulation workflow
│   └── settings/       # Settings page
├── components/
│   ├── ui/             # Base UI components
│   ├── layout/         # Layout components
│   ├── dashboard/      # Dashboard widgets
│   ├── forms/          # Form components
│   ├── jobs/           # Job-related components
│   └── viewer/         # Visualization components
├── hooks/              # Custom React hooks
├── stores/             # Zustand state stores
├── lib/                # Utilities and API client
└── types/              # TypeScript type definitions
```

## 🔧 Configuration

| Environment Variable           | Description                | Default                 |
| ------------------------------ | -------------------------- | ----------------------- |
| `NEXT_PUBLIC_API_URL`          | SurfScreen API server URL  | `http://localhost:8000` |
| `NEXT_PUBLIC_API_KEY`          | API authentication key     | -                       |
| `NEXT_PUBLIC_POLLING_INTERVAL` | Auto-refresh interval (ms) | `5000`                  |

## 🛠️ Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4
- **State Management**: Zustand
- **Data Fetching**: SWR
- **HTTP Client**: Axios
- **Charts**: Recharts
- **3D Visualization**: 3Dmol.js
- **Icons**: Lucide React
- **Toast**: React Hot Toast

## 📝 API Integration

The dashboard connects to the SurfScreen REST API:

- `GET /health` - Server health check
- `GET /api/v1/jobs` - List all jobs
- `POST /api/v1/screening` - Create screening job
- `POST /api/v1/md` - Create MD simulation job
- `GET /api/v1/jobs/{id}` - Get job details
- `DELETE /api/v1/jobs/{id}` - Cancel job

## 🔗 Related

- [SurfScreen](../) - Core surface adsorption screening library
- [API Documentation](../docs/api_guide.md) - REST API reference

## 📄 License

MIT License
