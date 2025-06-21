from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_, cast, Date
from sqlalchemy.sql import label
import math

from app import db
from app.models.user import User
from app.models.issue import Issue

from app.utils.location import get_location_data_from_coordinates

# Defina seu blueprint para a área administrativa
admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='templates/admin')

# Lista de empresas/órgãos
COMPANIES = [
    {"id": 1, "name": "Terracap"},
    {"id": 2, "name": "Neoenergia"},
    {"id": 3, "name": "SLU"},
    {"id": 4, "name": "Caesb"},
]

# Dicionário para acesso mais rápido
COMPANY_DICT = {company["id"]: company["name"] for company in COMPANIES}

# Função auxiliar para obter nome da empresa pelo ID
def get_company_name_by_id(company_id, default="Empresa não encontrada"):
    return COMPANY_DICT.get(company_id, default)

# Categorias de ocorrências - use seu próprio modelo ou tabela
CATEGORIES = [
    {"id": 1, "name": "Iluminação Pública"},
    {"id": 2, "name": "Buracos na Via"},
    {"id": 3, "name": "Lixo Acumulado"},
    {"id": 4, "name": "Risco de Inundação"},
    {"id": 5, "name": "Calçada Danificada"},
    {"id": 6, "name": "Árvore com Risco"},
]

# Dicionário para categorias
CATEGORY_DICT = {cat["id"]: cat["name"] for cat in CATEGORIES}

# Regiões administrativas (para Brasília)
REGIONS = [
    {"id": 1, "name": "Plano Piloto"},
    {"id": 2, "name": "Águas Claras"},
    {"id": 3, "name": "Taguatinga"},
    {"id": 4, "name": "Ceilândia"},
    {"id": 5, "name": "Guará"},
    {"id": 6, "name": "Sobradinho"},
]

# Mapeamento de status
STATUS_MAP = {
    'pendente': 'Pendente',
    'em_analise': 'Em Análise',
    'em_processamento': 'Em Processamento',
    'resolvido': 'Resolvido',
    'cancelado': 'Cancelado'
}

def get_category_name(category_id, default="Categoria desconhecida"):
    """
    Retorna o nome de uma categoria a partir do seu ID.
    Esta função é usada no template para exibir o nome da categoria
    identificada pela IA.
    """
    return CATEGORY_DICT.get(category_id, default)

# Rota principal do dashboard
@admin_bp.route('/')
def index():
    # Aqui carregamos os dados para o dashboard
    analytics_data = load_analytics_data()
    recent_reports = get_recent_reports()
    
    return render_template(
        'admin/dashboard.html',
        analytics=analytics_data,
        recent_reports=recent_reports,
        categories=CATEGORIES,
        regions=REGIONS
    )

# Função para carregar dados analíticos
def load_analytics_data(days=30, category_id=None, status=None, company=None):
    """
    Carrega todos os dados analíticos necessários para o dashboard
    com base nos dados reais do modelo Issue.
    """
    # Período de análise
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Filtros base
    filters = [Issue.created_at >= start_date, Issue.created_at <= end_date]
    
    if category_id and category_id != 'all':
        filters.append(Issue.category_id == int(category_id))
    
    if status and status != 'all':
        filters.append(Issue.status == status)
    
    if company and company != 'all':
        filters.append(Issue.companie == company)
    
    # Total de ocorrências no período
    total_reports = Issue.query.filter(*filters).count()
    
    # Ocorrências resolvidas
    resolved_filters = filters.copy()
    resolved_filters.append(Issue.status == 'resolvido')
    resolved_reports = Issue.query.filter(*resolved_filters).count()
    
    # Ocorrências ativas (não resolvidas)
    active_filters = filters.copy()
    active_filters.append(Issue.status != 'resolvido')
    active_reports = Issue.query.filter(*active_filters).count()
    
    # Calcular taxa de resolução
    resolved_percent = int((resolved_reports / total_reports) * 100) if total_reports > 0 else 0
    
    # Tempo médio de resolução
    # Subquery para obter a diferença entre created_at e updated_at para issues resolvidas
    resolution_time_query = db.session.query(
        func.avg(
            func.julianday(Issue.updated_at) - func.julianday(Issue.created_at)
        ).label('avg_days')
    ).filter(
        Issue.status == 'resolvido',
        *filters
    ).scalar()
    
    avg_resolution_time = f"{resolution_time_query:.1f} dias" if resolution_time_query else "N/A"
    
    # Gerar dados para o gráfico de tendência (ocorrências por dia)
    trend_dates = []
    new_reports_trend = []
    resolved_trend = []
    
    for i in range(days):
        day = start_date + timedelta(days=i)
        next_day = day + timedelta(days=1)
        day_str = day.strftime('%d/%m')
        trend_dates.append(day_str)
        
        # Novas ocorrências neste dia
        new_count = Issue.query.filter(
            Issue.created_at >= day,
            Issue.created_at < next_day
        ).count()
        new_reports_trend.append(new_count)
        
        # Ocorrências resolvidas neste dia
        resolved_count = Issue.query.filter(
            Issue.status == 'resolvido',
            Issue.updated_at >= day,
            Issue.updated_at < next_day
        ).count()
        resolved_trend.append(resolved_count)
    
    # Distribuição por categoria
    category_data = []
    category_labels = []
    
    category_counts = db.session.query(
        Issue.category_id,
        func.count(Issue.id).label('count')
    ).filter(*filters).group_by(Issue.category_id).all()
    
    for category_id, count in category_counts:
        category_name = CATEGORY_DICT.get(category_id, f"Categoria {category_id}")
        category_labels.append(category_name)
        category_data.append(count)
    
    # Desempenho por empresa/órgão
    agency_labels = []
    agency_resolution_time = []
    
    company_performance = db.session.query(
        Issue.companie,
        func.avg(
            func.julianday(Issue.updated_at) - func.julianday(Issue.created_at)
        ).label('avg_days')
    ).filter(
        Issue.status == 'resolvido',
        Issue.companie != None,
        *filters
    ).group_by(Issue.companie).all()
    
    for company, avg_days in company_performance:
        agency_labels.append(company)
        agency_resolution_time.append(round(avg_days, 1) if avg_days else 0)
    
    # Obter coordenadas para o mapa
    report_locations = []
    
    location_data = Issue.query.filter(*filters).order_by(desc(Issue.created_at)).limit(100).all()
    
    for issue in location_data:
        category_name = CATEGORY_DICT.get(issue.category_id, f"Categoria {issue.category_id}")
        status_name = STATUS_MAP.get(issue.status, issue.status)
        
        report_locations.append({
            "id": issue.id,
            "lat": issue.latitude,
            "lng": issue.longitude,
            "title": f"Ocorrência #{issue.issue_code}",
            "category": category_name,
            "status": status_name
        })
    
    # Calcular mudanças em relação ao período anterior
    # Período anterior
    previous_start = start_date - timedelta(days=days)
    previous_end = start_date
    
    previous_filters = [
        Issue.created_at >= previous_start,
        Issue.created_at <= previous_end
    ]
    
    if category_id and category_id != 'all':
        previous_filters.append(Issue.category_id == int(category_id))
    
    if status and status != 'all':
        previous_filters.append(Issue.status == status)
    
    if company and company != 'all':
        previous_filters.append(Issue.companie == company)
    
    previous_total = Issue.query.filter(*previous_filters).count()
    previous_resolved = Issue.query.filter(Issue.status == 'resolvido', *previous_filters).count()
    previous_active = Issue.query.filter(Issue.status != 'resolvido', *previous_filters).count()
    
    # Calcular variações percentuais
    reports_change = calculate_percent_change(previous_total, total_reports)
    resolution_change = calculate_percent_change(
        previous_resolved / previous_total if previous_total > 0 else 0,
        resolved_reports / total_reports if total_reports > 0 else 0
    )
    active_change = calculate_percent_change(previous_active, active_reports)
    
    # Variação no tempo de resolução
    previous_time_query = db.session.query(
        func.avg(
            func.julianday(Issue.updated_at) - func.julianday(Issue.created_at)
        ).label('avg_days')
    ).filter(
        Issue.status == 'resolvido',
        *previous_filters
    ).scalar()
    
    time_change = calculate_percent_change(previous_time_query or 0, resolution_time_query or 0)
    
    return {
        # KPIs
        "total_reports": total_reports,
        "resolved_percent": resolved_percent,
        "avg_resolution_time": avg_resolution_time,
        "active_reports": active_reports,
        
        # Mudanças
        "reports_change": reports_change,
        "resolution_change": resolution_change,
        "time_change": time_change,
        "active_change": active_change,
        
        # Dados de gráficos
        "trend_labels": trend_dates,
        "new_reports_trend": new_reports_trend,
        "resolved_trend": resolved_trend,
        "category_labels": category_labels,
        "category_data": category_data,
        "agency_labels": agency_labels,
        "agency_resolution_time": agency_resolution_time,
        "report_locations": report_locations
    }

def calculate_percent_change(old_value, new_value):
    """Calcula a variação percentual entre dois valores"""
    if old_value == 0:
        return 100 if new_value > 0 else 0
    
    change = ((new_value - old_value) / old_value) * 100
    return round(change)

# Função para obter ocorrências recentes
def get_recent_reports(limit=10):
    """
    Obtém as ocorrências mais recentes para exibição no dashboard.
    """
    recent_issues = Issue.query.order_by(desc(Issue.created_at)).limit(limit).all()
    
    reports = []
    for issue in recent_issues:
        # Obter nome da categoria
        category_name = CATEGORY_DICT.get(issue.category_id, f"Categoria {issue.category_id}")
        
        # Mapear status para um nome amigável
        status_name = STATUS_MAP.get(issue.status, issue.status)
        
        # Localização aproximada baseada nas coordenadas
        # Em um sistema real, você faria geocodificação reversa aqui
        location = f"Lat: {issue.latitude:.4f}, Long: {issue.longitude:.4f}"
        
        reports.append({
            "id": issue.issue_code,
            "title": issue.description[:50] + "..." if len(issue.description) > 50 else issue.description,
            "category": category_name,
            "location": location,
            "date": issue.created_at.strftime('%d/%m/%Y'),
            "agency": issue.companie or "Não atribuído",
            "status": status_name
        })
    
    return reports
    """
    Endpoint para filtrar dados analíticos via AJAX.
    Retorna dados JSON filtrados com base nos parâmetros recebidos.
    """
    period = request.form.get('period', '30')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    category = request.form.get('category', 'all')
    status = request.form.get('status', 'all')
    company = request.form.get('company', 'all')
    
    # Determinar o número de dias para análise
    days = int(period) if period != 'custom' else None
    
    if period == 'custom' and start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        days = (end - start).days
    
    # Carregar dados analíticos com os filtros aplicados
    analytics_data = load_analytics_data(
        days=days,
        category_id=category,
        status=status,
        company=company
    )
    
    return jsonify(analytics_data)

# Classe auxiliar para paginação
class Pagination:
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count
        self.pages = int(math.ceil(total_count / float(per_page)))
        
    @property
    def total_items(self):
        return self.total_count
        
    @property
    def has_prev(self):
        return self.page > 1
        
    @property
    def has_next(self):
        return self.page < self.pages
        
    @property
    def start_index(self):
        return (self.page - 1) * self.per_page + 1
        
    @property
    def end_index(self):
        end = self.page * self.per_page
        return min(end, self.total_count)
        
    def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or
                (num > self.page - left_current - 1 and
                 num < self.page + right_current) or
                num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num

# Rota para mostrar detalhes de uma ocorrência específica
@admin_bp.route('/issue/<issue_code>')
def issue_detail(issue_code):
    issue = Issue.query.filter_by(issue_code=issue_code).first_or_404()
    
    category_name = CATEGORY_DICT.get(issue.category_id, f"Categoria {issue.category_id}")
    status_name = STATUS_MAP.get(issue.status, issue.status)
    location_data= get_location_data_from_coordinates(issue.latitude, issue.longitude)
    
    # Calcular tempo de resolução se resolvido
    resolution_time = None
    if issue.status == 'resolvido':
        delta = issue.updated_at - issue.created_at
        resolution_time = f"{delta.days} dias, {delta.seconds // 3600} horas"
    
    # Obter dados de localização a partir das coordenadas
    location_data = get_location_data_from_coordinates(issue.latitude, issue.longitude)
    
    return render_template(
        'admin/issue_detail.html',
        issue=issue,
        category_name=category_name,
        status_name=status_name,
        resolution_time=resolution_time,
        location_data=location_data,
        STATUS_MAP=STATUS_MAP,  # Passando o mapeamento de status para o template
        get_category_name=get_category_name  # Passando a função helper para o template
    )

# Rota para atualizar o status de uma ocorrência
@admin_bp.route('/issue/<issue_code>/update-status', methods=['POST'])
def update_issue_status(issue_code):
    issue = Issue.query.filter_by(issue_code=issue_code).first_or_404()
    
    new_status = request.form.get('status')
    company = request.form.get('company')
    
    if new_status and new_status in STATUS_MAP:
        issue.status = new_status
        
    if company:
        issue.companie = company
    
    issue.updated_at = datetime.now()
    db.session.commit()
    
    flash(f'Status da ocorrência {issue_code} atualizado com sucesso!', 'success')
    return redirect(url_for('admin.issue_detail', issue_code=issue_code))

# Função load_analytics_data atualizada para fornecer dados corretos para o dashboard ajustado
def load_analytics_data(days=30, category_id=None, status=None, company=None):
    """
    Carrega todos os dados analíticos necessários para o dashboard
    com base nos dados reais do modelo Issue.
    """
    # Período de análise
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Filtros base
    filters = [Issue.created_at >= start_date, Issue.created_at <= end_date]
    
    if category_id and category_id != 'all':
        filters.append(Issue.category_id == int(category_id))
    
    if status and status != 'all':
        filters.append(Issue.status == status)
    
    if company and company != 'all':
        filters.append(Issue.companie == company)
    
    # Total de ocorrências no período
    total_reports = Issue.query.filter(*filters).count()
    
    # Ocorrências por status
    pending_reports = Issue.query.filter(Issue.status == 'pendente', *filters).count()
    processing_reports = Issue.query.filter(Issue.status.in_(['em_analise', 'em_processamento']), *filters).count()
    resolved_reports = Issue.query.filter(Issue.status == 'resolvido', *filters).count()
    
    # Gerar dados para o gráfico de tendência (ocorrências por dia)
    trend_dates = []
    new_reports_trend = []
    resolved_trend = []
    
    for i in range(days):
        day = start_date + timedelta(days=i)
        next_day = day + timedelta(days=1)
        day_str = day.strftime('%d/%m')
        trend_dates.append(day_str)
        
        # Novas ocorrências neste dia
        day_filters = filters.copy()
        day_filters[0] = Issue.created_at >= day
        day_filters[1] = Issue.created_at < next_day
        
        new_count = Issue.query.filter(*day_filters).count()
        new_reports_trend.append(new_count)
        
        # Ocorrências resolvidas neste dia
        resolved_day_filters = filters.copy()
        resolved_day_filters.append(Issue.status == 'resolvido')
        resolved_day_filters[0] = Issue.updated_at >= day
        resolved_day_filters[1] = Issue.updated_at < next_day
        
        resolved_count = Issue.query.filter(*resolved_day_filters).count()
        resolved_trend.append(resolved_count)
    
    # Distribuição por categoria
    category_data = []
    category_labels = []
    
    category_counts = db.session.query(
        Issue.category_id,
        func.count(Issue.id).label('count')
    ).filter(*filters).group_by(Issue.category_id).all()
    
    for category_id, count in category_counts:
        category_name = CATEGORY_DICT.get(category_id, f"Categoria {category_id}")
        category_labels.append(category_name)
        category_data.append(count)
    
    # Ocorrências por órgão (quantidade, não desempenho)
    agency_labels = []
    agency_count = []
    
    company_counts = db.session.query(
        Issue.companie,
        func.count(Issue.id).label('count')
    ).filter(
        Issue.companie != None,
        *filters
    ).group_by(Issue.companie).all()
    
    for company, count in company_counts:
        agency_labels.append(company)
        agency_count.append(count)
    
    # Adicionar "Não atribuído" se houver ocorrências sem órgão atribuído
    unassigned_count = Issue.query.filter(Issue.companie == None, *filters).count()
    if unassigned_count > 0:
        agency_labels.append("Não atribuído")
        agency_count.append(unassigned_count)
    
    # Obter coordenadas para o mapa
    report_locations = []
    
    location_data = Issue.query.filter(*filters).order_by(desc(Issue.created_at)).limit(100).all()
    
    for issue in location_data:
        category_name = CATEGORY_DICT.get(issue.category_id, f"Categoria {issue.category_id}")
        status_name = STATUS_MAP.get(issue.status, issue.status)
        
        report_locations.append({
            "id": issue.issue_code,
            "lat": issue.latitude,
            "lng": issue.longitude,
            "title": f"Ocorrência #{issue.issue_code}",
            "category": category_name,
            "status": status_name
        })
    
    # Calcular mudanças em relação ao período anterior
    # Período anterior
    previous_start = start_date - timedelta(days=days)
    previous_end = start_date
    
    previous_filters = [
        Issue.created_at >= previous_start,
        Issue.created_at <= previous_end
    ]
    
    if category_id and category_id != 'all':
        previous_filters.append(Issue.category_id == int(category_id))
    
    if status and status != 'all':
        previous_filters.append(Issue.status == status)
    
    if company and company != 'all':
        previous_filters.append(Issue.companie == company)
    
    previous_total = Issue.query.filter(*previous_filters).count()
    previous_pending = Issue.query.filter(Issue.status == 'pendente', *previous_filters).count()
    previous_processing = Issue.query.filter(Issue.status.in_(['em_analise', 'em_processamento']), *previous_filters).count()
    previous_resolved = Issue.query.filter(Issue.status == 'resolvido', *previous_filters).count()
    
    # Calcular variações percentuais
    reports_change = calculate_percent_change(previous_total, total_reports)
    pending_change = calculate_percent_change(previous_pending, pending_reports)
    processing_change = calculate_percent_change(previous_processing, processing_reports)
    resolved_change = calculate_percent_change(previous_resolved, resolved_reports)
    
    return {
        # KPIs
        "total_reports": total_reports,
        "pending_reports": pending_reports,
        "processing_reports": processing_reports,
        "resolved_reports": resolved_reports,
        
        # Mudanças
        "reports_change": reports_change,
        "pending_change": pending_change,
        "processing_change": processing_change,
        "resolved_change": resolved_change,
        
        # Dados de gráficos
        "trend_labels": trend_dates,
        "new_reports_trend": new_reports_trend,
        "resolved_trend": resolved_trend,
        "category_labels": category_labels,
        "category_data": category_data,
        "agency_labels": agency_labels,
        "agency_count": agency_count,  # Mudado de agency_resolution_time para agency_count
        "report_locations": report_locations
    }

# Rota para filtros AJAX
@admin_bp.route('/filter-analytics', methods=['POST'])
def filter_analytics():
    """
    Endpoint para filtrar dados analíticos via AJAX.
    Retorna dados JSON filtrados com base nos parâmetros recebidos.
    """
    period = request.form.get('period', '30')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    category = request.form.get('category', 'all')
    status = request.form.get('status', 'all')
    company = request.form.get('company', 'all')
    
    # Determinar o número de dias para análise
    days = int(period) if period != 'custom' else None
    
    if period == 'custom' and start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        days = (end - start).days + 1  # +1 para incluir o dia final
    
    # Carregar dados analíticos com os filtros aplicados
    analytics_data = load_analytics_data(
        days=days if days else 30,
        category_id=category,
        status=status,
        company=company
    )
    
    return jsonify(analytics_data)

# Rota para listar todas as ocorrências
@admin_bp.route('/issues')
def issues():
    # Obter parâmetros da query string
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', 'all')
    category_id = request.args.get('category', 'all')
    company = request.args.get('company', 'all')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'date')
    order = request.args.get('order', 'desc')
    
    # Construir a query base
    query = Issue.query
    
    # Aplicar filtros
    if status != 'all':
        query = query.filter(Issue.status == status)
        
    if category_id != 'all':
        try:
            query = query.filter(Issue.category_id == int(category_id))
        except ValueError:
            pass
            
    if company == 'unassigned':
        query = query.filter(Issue.companie == None)
    elif company != 'all':
        query = query.filter(Issue.companie == company)
        
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Issue.created_at >= from_date)
        except ValueError:
            pass
            
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date.replace(hour=23, minute=59, second=59)
            query = query.filter(Issue.created_at <= to_date)
        except ValueError:
            pass
            
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            # Busca por código da ocorrência ou descrição
            db.or_(
                Issue.issue_code.like(search_term),
                Issue.description.like(search_term)
            )
        )
    
    # Aplicar ordenação
    if sort == 'date':
        query = query.order_by(desc(Issue.created_at) if order == 'desc' else Issue.created_at)
    elif sort == 'status':
        query = query.order_by(Issue.status)
    elif sort == 'company':
        query = query.order_by(Issue.companie)
    elif sort == 'category':
        query = query.order_by(Issue.category_id)
    else:
        # Ordenação padrão: data decrescente (mais recentes primeiro)
        query = query.order_by(desc(Issue.created_at))
    
    # Contar o total de itens (para paginação)
    total_count = query.count()
    
    # Paginar os resultados
    issues = query.paginate(page=page, per_page=per_page, error_out=False).items
    
    # Criar objeto de paginação personalizado
    pagination = Pagination(page, per_page, total_count)
    
    # Estatísticas rápidas
    stats = {
        'total': Issue.query.count(),
        'pending': Issue.query.filter(Issue.status == 'pendente').count(),
        'processing': Issue.query.filter(Issue.status.in_(['em_analise', 'em_processamento'])).count(),
        'resolved': Issue.query.filter(Issue.status == 'resolvido').count()
    }
    
    # Obter lista de categorias
    categories = [
        {"id": cat["id"], "name": cat["name"]} for cat in CATEGORIES
    ]
    
    # Obter lista de empresas/órgãos
    companies = [
        {"id": company["id"], "name": company["name"]} for company in COMPANIES
    ]
    
    return render_template(
        'admin/issues.html',
        issues=issues,
        pagination=pagination,
        stats=stats,
        categories=categories,
        companies=companies,
        get_category_name=get_category_name
    )

# Rota para atualização rápida de status via AJAX
@admin_bp.route('/issues/update-status', methods=['POST'])
def update_issue_status_ajax():
    issue_id = request.form.get('issue_id')
    status = request.form.get('status')
    company = request.form.get('company')
    observation = request.form.get('observation')
    
    if not issue_id or not status:
        return jsonify({
            'success': False,
            'message': 'ID da ocorrência e status são obrigatórios'
        })
    
    try:
        issue = Issue.query.get(issue_id)
        if not issue:
            return jsonify({
                'success': False,
                'message': 'Ocorrência não encontrada'
            })
        
        # Atualizar o status
        issue.status = status
        
        # Atualizar a empresa se fornecida
        if company:
            issue.companie = company
        
        # Registrar a observação (se você tiver um modelo para isso)
        # Se você tiver um modelo para histórico de atualizações, seria algo como:
        # if observation:
        #     history = IssueHistory(
        #         issue_id=issue.id,
        #         user_id=current_user.id,
        #         action='status_update',
        #         old_status=old_status,
        #         new_status=status,
        #         observation=observation
        #     )
        #     db.session.add(history)
        
        # Atualizar timestamp
        issue.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Status atualizado com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar status: {str(e)}'
        })