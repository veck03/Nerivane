import './about-developer.css'

const developer = {
  name: 'Vansh Tomar',
  phone: '+91 7999826982',
  location: 'Madhya Pradesh, India',
  email: 'vansh.tomar.0306@gmail.com',
  linkedin: 'https://www.linkedin.com/in/vansh-tomar03/',
  github: 'https://github.com/veck03',
  portfolio: 'https://veck03.github.io/portfolio/',
  about: 'Mathematics and Computing undergraduate with hands-on project experience in machine learning, scientific data processing, and LLM-powered retrieval systems. Interested in developing practical AI solutions, with a particular focus on agentic AI, deep learning, and geospatial applications.',
}

const education = [
  { institution: 'Madhav Institute of Technology and Science', degree: 'B.Tech. in Mathematics and Computing CGPA: 9.17', location: 'Gwalior, India', period: 'Aug 2025 – Expected Aug 2029' },
  { institution: 'Swami Vivekananda Academy', degree: 'CBSE Class 12th PCM, Percentage: 91.8%', location: 'Gwalior, India', period: 'Apr 2023 – Jun 2024' },
]

const projects = [
  { title: 'Agentic Scientific Research Assistant', badge: 'Core project', stack: ['Python', 'RAG', 'ChromaDB', 'Sentence Transformers', 'Groq API'], bullets: ['Developed an agentic RAG system for scientific research, integrating retrieval from oceanographic research papers with structured oceanographic data.', 'Implemented document retrieval using BM25 and vector search, followed by cross-encoder reranking to improve the relevance of retrieved research passages.', 'Built an LLM-based query router using Groq API to direct queries to paper retrieval, dataset analysis, or combined workflows, enabling evidence-based responses.'] },
  { title: 'Neural Network from Scratch', badge: 'Deep learning foundations', stack: ['Python', 'NumPy'], bullets: ['Implemented a neural network from scratch in Python and NumPy to understand the mathematical foundations of forward propagation and backpropagation.', 'Built core components including weighted layers, activation functions, loss computation, gradient calculation, and parameter updates.', 'Trained and evaluated the model while analyzing learning behavior without relying on high-level deep learning frameworks.'] },
  { title: 'Urban Heat Mitigation using AI/ML', badge: 'Geospatial AI', stack: ['Python', 'Google Earth Engine', 'Remote Sensing'], bullets: ['Developing an ML-based approach to analyze urban heat patterns in Delhi using satellite-derived environmental and urban features.', 'Processed Landsat and Sentinel-2 imagery to derive Land Surface Temperature, NDVI, NDWI, EVI, and NDBI.', 'Engineered geospatial features including land cover, tree cover, population density, elevation, slope, and distance to water for urban heat analysis.'] },
]

const skills = [
  { category: 'Programming', items: ['Python', 'C++'] },
  { category: 'AI / Machine Learning', items: ['Machine Learning', 'Neural Networks', 'Large Language Models', 'RAG', 'Agentic AI'] },
  { category: 'Libraries & Frameworks', items: ['NumPy', 'Pandas', 'Scikit-learn', 'Sentence Transformers', 'ChromaDB', 'FastAPI', 'LangChain'] },
  { category: 'Developer Tools', items: ['Git', 'GitHub', 'Jupyter Notebook', 'VS Code'] },
]

function SectionTitle({ children, note }) {
  return <div className="about-section-heading"><h2>{children}</h2>{note && <span>{note}</span>}</div>
}

export default function AboutDeveloper() {
  return <div className="about-developer">
    <section className="about-profile-card">
      <div className="about-profile-top">
        <div>
          <span className="about-role">System architect & developer</span>
          <h2>{developer.name}</h2>
          <div className="about-contact">
            <span><span aria-hidden="true">⌖</span>{developer.location}</span>
            <a href={`tel:${developer.phone.replaceAll(' ', '')}`}><span aria-hidden="true">☎</span>{developer.phone}</a>
            <a href={`mailto:${developer.email}`}><span aria-hidden="true">✉</span>{developer.email}</a>
          </div>
        </div>
        <div className="about-social-links">
          <a className="about-github" href={developer.github} target="_blank" rel="noreferrer">GitHub <span aria-hidden="true">↗</span></a>
          <a className="about-linkedin" href={developer.linkedin} target="_blank" rel="noreferrer">LinkedIn <span aria-hidden="true">↗</span></a>
          <a className="about-portfolio" href={developer.portfolio} target="_blank" rel="noreferrer">Portfolio <span aria-hidden="true">↗</span></a>
        </div>
      </div>
      <div className="about-bio"><h3>About & research motivation</h3><p>{developer.about}</p></div>
    </section>

    <div className="about-content-grid">
      <section className="about-projects">
        <SectionTitle note={`${projects.length} featured projects`}>Projects & systems</SectionTitle>
        <div className="about-project-list">{projects.map((project) => <article className="about-project-card" key={project.title}>
          <div className="about-project-heading"><h3>{project.title}</h3><span>{project.badge}</span></div>
          <div className="about-tags">{project.stack.map((tech) => <span key={tech}>{tech}</span>)}</div>
          <ul>{project.bullets.map((bullet) => <li key={bullet}>{bullet}</li>)}</ul>
        </article>)}</div>
      </section>
      <aside className="about-sidebar-content">
        <section><SectionTitle>Education</SectionTitle><div className="about-education-list">{education.map((item) => <article className="about-education-card" key={item.institution}>
          <h3>{item.institution}</h3><p>{item.degree.split(/(CGPA: 9\.17|91\.8%)/).map((part) => /^(CGPA: 9\.17|91\.8%)$/.test(part) ? <strong className="about-academic-score" key={part}>{part}</strong> : part)}</p><div><span>{item.location}</span><span>{item.period}</span></div>
        </article>)}</div></section>
        <section><SectionTitle>Technical competencies</SectionTitle><div className="about-skills-card">{skills.map((group) => <div className="about-skill-group" key={group.category}>
          <h3>{group.category}</h3><div className="about-tags">{group.items.map((skill) => <span key={skill}>{skill}</span>)}</div>
        </div>)}</div></section>
      </aside>
    </div>
  </div>
}
