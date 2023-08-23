# Generated by Django 4.1.10 on 2023-08-23 21:27

from django.db import migrations, models
import journal.models


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="journal",
            name="subject_areas",
            field=journal.models.ModifiedArrayField(
                base_field=models.CharField(
                    blank=True,
                    choices=[
                        ("Ciências Agrárias", "Ciências Agrárias"),
                        ("Ciências Biológicas", "Ciências Biológicas"),
                        ("Ciências Exatas e da Terra", "Ciências Exatas e da Terra"),
                        ("Ciências Humanas", "Ciências Humanas"),
                        ("Ciências Sociais Aplicadas", "Ciências Sociais Aplicadas"),
                        ("Ciências da Saúde", "Ciências da Saúde"),
                        ("Engenharias", "Engenharias"),
                        ("Lingüística, Letras e Artes", "Lingüística, Letras e Artes"),
                        ("Multidisciplinar", "Multidisciplinar"),
                    ],
                    max_length=100,
                    null=True,
                    verbose_name="Thematic Areas",
                ),
                blank=True,
                null=True,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="journal",
            name="wos_areas",
            field=journal.models.ModifiedArrayField(
                base_field=models.CharField(
                    blank=True,
                    choices=[
                        ("Abuse", "Abuse"),
                        ("Acústica", "Acústica"),
                        ("Administration", "Administration"),
                        ("Aerospace", "Aerospace"),
                        ("African", "African"),
                        ("Agricultural", "Agricultural"),
                        ("Agriculture", "Agriculture"),
                        ("Agronomia", "Agronomia"),
                        ("Alergia", "Alergia"),
                        ("American", "American"),
                        ("Analytical", "Analytical"),
                        ("Anatomy", "Anatomy"),
                        ("Andrologia", "Andrologia"),
                        ("Anestesiologia", "Anestesiologia"),
                        ("Animal", "Animal"),
                        ("Antropologia", "Antropologia"),
                        ("Applications", "Applications"),
                        ("Applied", "Applied"),
                        ("Area", "Area"),
                        ("Arqueologia", "Arqueologia"),
                        ("Arquitetura", "Arquitetura"),
                        ("Arte", "Arte"),
                        ("Artificial", "Artificial"),
                        ("Asian", "Asian"),
                        ("Astronomy", "Astronomy"),
                        ("Astrophysics", "Astrophysics"),
                        ("Atmospheric", "Atmospheric"),
                        ("Atomic", "Atomic"),
                        ("Audiology", "Audiology"),
                        ("Australian", "Australian"),
                        ("Automation", "Automation"),
                        ("Behavioral", "Behavioral"),
                        ("Biochemical", "Biochemical"),
                        ("Biochemistry", "Biochemistry"),
                        ("Biodiversity", "Biodiversity"),
                        ("Biologia", "Biologia"),
                        ("Biological", "Biological"),
                        ("Biomaterials", "Biomaterials"),
                        ("Biomedical", "Biomedical"),
                        ("Biophysics", "Biophysics"),
                        ("Biotechnology", "Biotechnology"),
                        ("British", "British"),
                        ("Building", "Building"),
                        ("Canadian", "Canadian"),
                        ("Cardiac", "Cardiac"),
                        ("Cardiovascular", "Cardiovascular"),
                        ("Care", "Care"),
                        ("Cell", "Cell"),
                        ("Ceramics", "Ceramics"),
                        ("Characterization", "Characterization"),
                        ("Chemical", "Chemical"),
                        ("Chemistry", "Chemistry"),
                        ("Cirurgia", "Cirurgia"),
                        ("Civil", "Civil"),
                        ("Clinical", "Clinical"),
                        ("Clássicos", "Clássicos"),
                        ("Coatings", "Coatings"),
                        ("Complementary", "Complementary"),
                        ("Composites", "Composites"),
                        ("Computer", "Computer"),
                        ("Comunicação", "Comunicação"),
                        ("Conservation", "Conservation"),
                        ("Construction", "Construction"),
                        ("Control", "Control"),
                        ("Criminology", "Criminology"),
                        ("Cristalografia", "Cristalografia"),
                        ("Critical", "Critical"),
                        ("Criticism", "Criticism"),
                        ("Cultural", "Cultural"),
                        ("Cybernetics", "Cybernetics"),
                        ("Dairy", "Dairy"),
                        ("Dança", "Dança"),
                        ("Demografia", "Demografia"),
                        ("Dentistry", "Dentistry"),
                        ("Dermatologia", "Dermatologia"),
                        ("Development", "Development"),
                        ("Developmental", "Developmental"),
                        ("Dietetics", "Dietetics"),
                        ("Disciplines", "Disciplines"),
                        ("Disease", "Disease"),
                        ("Diseases", "Diseases"),
                        ("Dutch", "Dutch"),
                        ("Ecologia", "Ecologia"),
                        ("Economia", "Economia"),
                        ("Education", "Education"),
                        ("Educational", "Educational"),
                        ("Electrical", "Electrical"),
                        ("Electronic", "Electronic"),
                        ("Eletroquímica", "Eletroquímica"),
                        ("Emergency", "Emergency"),
                        ("Endocrinology", "Endocrinology"),
                        ("Energy", "Energy"),
                        ("Enfermagem", "Enfermagem"),
                        ("Engineering", "Engineering"),
                        ("Entomologia", "Entomologia"),
                        ("Environmental", "Environmental"),
                        ("Espectroscopia", "Espectroscopia"),
                        ("Ethnic", "Ethnic"),
                        ("Evolutionary", "Evolutionary"),
                        ("Experimental", "Experimental"),
                        ("Family", "Family"),
                        ("Fields", "Fields"),
                        ("Film", "Film"),
                        ("Films", "Films"),
                        ("Filosofia", "Filosofia"),
                        ("Finance", "Finance"),
                        ("Fisiologia", "Fisiologia"),
                        ("Folclore", "Folclore"),
                        ("Food", "Food"),
                        ("Freshwater", "Freshwater"),
                        ("Fuels", "Fuels"),
                        ("Gastroenterology", "Gastroenterology"),
                        ("General", "General"),
                        ("Genetics", "Genetics"),
                        ("Geochemistry", "Geochemistry"),
                        ("Geografia", "Geografia"),
                        ("Geologia", "Geologia"),
                        ("Geological", "Geological"),
                        ("Geophysics", "Geophysics"),
                        ("Geosciences", "Geosciences"),
                        ("Gerenciamento", "Gerenciamento"),
                        ("Geriatrics", "Geriatrics"),
                        ("German", "German"),
                        ("Gerontologia", "Gerontologia"),
                        ("Gynecology", "Gynecology"),
                        ("Hardware", "Hardware"),
                        ("Health", "Health"),
                        ("Hematologia", "Hematologia"),
                        ("Hepatology", "Hepatology"),
                        ("Heredity", "Heredity"),
                        ("História", "História"),
                        ("Horticultura", "Horticultura"),
                        ("Hospitality", "Hospitality"),
                        ("Humanities", "Humanities"),
                        ("Imaging", "Imaging"),
                        ("Imunologia", "Imunologia"),
                        ("Industrial", "Industrial"),
                        ("Infectious", "Infectious"),
                        ("Informatics", "Informatics"),
                        ("Information", "Information"),
                        ("Inorganic", "Inorganic"),
                        ("Instrumentation", "Instrumentation"),
                        ("Instruments", "Instruments"),
                        ("Integrative", "Integrative"),
                        ("Intelligence", "Intelligence"),
                        ("Interdisciplinary", "Interdisciplinary"),
                        ("Internal", "Internal"),
                        ("International", "International"),
                        ("Isles", "Isles"),
                        ("Issues", "Issues"),
                        ("Labor", "Labor"),
                        ("Laboratory", "Laboratory"),
                        ("Language", "Language"),
                        ("Legal", "Legal"),
                        ("Lei", "Lei"),
                        ("Leisure", "Leisure"),
                        ("Library", "Library"),
                        ("Limnologia", "Limnologia"),
                        ("Linguística", "Linguística"),
                        ("Literary", "Literary"),
                        ("Literatura", "Literatura"),
                        ("Manufacturing", "Manufacturing"),
                        ("Marine", "Marine"),
                        ("Matemática", "Matemática"),
                        ("Materials", "Materials"),
                        ("Mathematical", "Mathematical"),
                        ("Mechanical", "Mechanical"),
                        ("Mecânica", "Mecânica"),
                        ("Medical", "Medical"),
                        ("Medicinal", "Medicinal"),
                        ("Medicine", "Medicine"),
                        ("Medieval", "Medieval"),
                        ("Metabolism", "Metabolism"),
                        ("Metallurgical", "Metallurgical"),
                        ("Metallurgy", "Metallurgy"),
                        ("Meteorology", "Meteorology"),
                        ("Methods", "Methods"),
                        ("Micologia", "Micologia"),
                        ("Microbiologia", "Microbiologia"),
                        ("Mineral", "Mineral"),
                        ("Mineralogy", "Mineralogy"),
                        ("Mining", "Mining"),
                        ("Molecular", "Molecular"),
                        ("Morphology", "Morphology"),
                        ("Multidisciplinary", "Multidisciplinary"),
                        ("Música", "Música"),
                        ("Nanoscience", "Nanoscience"),
                        ("Nanotechnology", "Nanotechnology"),
                        ("Negócios", "Negócios"),
                        ("Nephrology", "Nephrology"),
                        ("Neurociências", "Neurociências"),
                        ("Neurology", "Neurology"),
                        ("Nuclear", "Nuclear"),
                        ("Nutrition", "Nutrition"),
                        ("Obstetrics", "Obstetrics"),
                        ("Occupational", "Occupational"),
                        ("Ocean", "Ocean"),
                        ("Oceanografia", "Oceanografia"),
                        ("Oftalmologia", "Oftalmologia"),
                        ("Oncologia", "Oncologia"),
                        ("Operations", "Operations"),
                        ("Oral", "Oral"),
                        ("Organic", "Organic"),
                        ("Ornitologia", "Ornitologia"),
                        ("Ortopedia", "Ortopedia"),
                        ("Otorrinolaringologia", "Otorrinolaringologia"),
                        ("Paleontologia", "Paleontologia"),
                        ("Paper", "Paper"),
                        ("Parasitologia", "Parasitologia"),
                        ("Particles", "Particles"),
                        ("Patologia", "Patologia"),
                        ("Pediatria", "Pediatria"),
                        ("Penology", "Penology"),
                        ("Peripheral", "Peripheral"),
                        ("Pesca", "Pesca"),
                        ("Petroleum", "Petroleum"),
                        ("Pharmacology", "Pharmacology"),
                        ("Pharmacy", "Pharmacy"),
                        ("Physical", "Physical"),
                        ("Physics", "Physics"),
                        ("Planning", "Planning"),
                        ("Plant", "Plant"),
                        ("Poesia", "Poesia"),
                        ("Policy", "Policy"),
                        ("Political", "Political"),
                        ("Polymer", "Polymer"),
                        ("Primary", "Primary"),
                        ("Probability", "Probability"),
                        ("Processing", "Processing"),
                        ("Psicologia", "Psicologia"),
                        ("Psiquiatria", "Psiquiatria"),
                        ("Psychoanalysis", "Psychoanalysis"),
                        ("Public", "Public"),
                        ("Radio", "Radio"),
                        ("Radiology", "Radiology"),
                        ("Reabilitação", "Reabilitação"),
                        ("Relations", "Relations"),
                        ("Religião", "Religião"),
                        ("Remote", "Remote"),
                        ("Renaissance", "Renaissance"),
                        ("Reproductive", "Reproductive"),
                        ("Research", "Research"),
                        ("Resources", "Resources"),
                        ("Respiratory", "Respiratory"),
                        ("Reumatologia", "Reumatologia"),
                        ("Reviews", "Reviews"),
                        ("Robótica", "Robótica"),
                        ("Romance", "Romance"),
                        ("Scandinavian", "Scandinavian"),
                        ("Science", "Science"),
                        ("Sciences", "Sciences"),
                        ("Scientific", "Scientific"),
                        ("Sensing", "Sensing"),
                        ("Services", "Services"),
                        ("Silvicultura", "Silvicultura"),
                        ("Social", "Social"),
                        ("Sociologia", "Sociologia"),
                        ("Software", "Software"),
                        ("Soil", "Soil"),
                        ("Special", "Special"),
                        ("Speech", "Speech"),
                        ("Sport", "Sport"),
                        ("Statistics", "Statistics"),
                        ("Studies", "Studies"),
                        ("Substance", "Substance"),
                        ("System", "System"),
                        ("Systems", "Systems"),
                        ("Technology", "Technology"),
                        ("Telecomunicações", "Telecomunicações"),
                        ("Television", "Television"),
                        ("Testing", "Testing"),
                        ("Textiles", "Textiles"),
                        ("Theater", "Theater"),
                        ("Theory", "Theory"),
                        ("Tourism", "Tourism"),
                        ("Toxicologia", "Toxicologia"),
                        ("Transporte", "Transporte"),
                        ("Tropical", "Tropical"),
                        ("Urban", "Urban"),
                        ("Urology", "Urology"),
                        ("Vascular", "Vascular"),
                        ("Veterinary", "Veterinary"),
                        ("Water", "Water"),
                        ("Women's", "Women's"),
                        ("Wood", "Wood"),
                        ("Work", "Work"),
                        ("Zoologia", "Zoologia"),
                        ("Ética", "Ética"),
                        ("Óptica", "Óptica"),
                    ],
                    max_length=100,
                    null=True,
                    verbose_name="WOS Thematic Areas",
                ),
                blank=True,
                null=True,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="journal",
            name="wos_db",
            field=journal.models.ModifiedArrayField(
                base_field=models.CharField(
                    blank=True,
                    choices=[
                        ("A&HCI", "Arts Humanities Citation Index"),
                        ("SCIE-E", "Science Citation Index Expanded"),
                        ("SSCI", "Social Sciences Citation Index"),
                    ],
                    max_length=100,
                    null=True,
                    verbose_name="Web of Knowledge Databases",
                ),
                blank=True,
                null=True,
                size=None,
            ),
        ),
    ]
