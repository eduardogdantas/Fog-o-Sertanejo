import tkinter as tk
from tkinter import messagebox, ttk
import banco   
class AplicativoRestaurante:
    def __init__(self, root):
        self.root = root  
        
        # 1. DEFINIÇÃO DAS VARIÁVEIS (Isso corrige o erro)
        self.usuario_logado = "ADMIN" 
        self.caixa_aberto = False 
        
        # 2. CONFIGURAÇÕES DA JANELA
        self.root.title("Sistema CUMMINS")
        self.root.geometry("1200x780")
        self.root.configure(bg="#f0f0f0")
        
        # 3. LÓGICA E CENTRALIZAÇÃO
        self.verificar_status_caixa_inicial()
        self.centralizar_janela(self.root, 1200, 780)
        
        # 4. CRIAÇÃO DOS ELEMENTOS DA INTERFACE
        self.frame_menu = tk.Frame(self.root, bg="#dcdcdc", height=110, bd=1, relief="raised")
        self.frame_menu.pack(fill="x", side="top")
        self.frame_menu.pack_propagate(False)
        
        self.criar_botoes_menu()
        
        # A partir daqui, self.usuario_logado já existe e o erro não ocorrerá
        self.barra_status = tk.Label(
            self.root, 
            text=f"PAINEL PRINCIPAL | OPERADOR ATUAL: {self.usuario_logado.upper()}", 
            bg="#2c5ca4", 
            fg="white", 
            font=("Arial", 11, "bold"), 
            anchor="center", 
            height=2
        )
        self.barra_status.pack(fill="x")
        
        self.container_principal = tk.Frame(self.root, bg="#f0f0f0")
        self.container_principal.pack(fill="both", expand=True)
        
        self.carregar_aba_vendas_inicial()

    def verificar_status_caixa_inicial(self):
        try:
            movimentacoes = banco.obter_fluxo_caixa_dia()
            if movimentacoes:
                ultima_mov = movimentacoes[-1][0] 
                if "Abertura" in ultima_mov or "Suprimento" in ultima_mov or "Sangria" in ultima_mov:
                    self.caixa_aberto = True
                if "Fechamento" in ultima_mov:
                    self.caixa_aberto = False
        except:
            self.caixa_aberto = False

    def centralizar_janela(self, janela, largura, altura):
        largura_tela = janela.winfo_screenwidth()
        altura_tela = janela.winfo_screenheight()
        x = (largura_tela // 2) - (largura // 2)
        y = (altura_tela // 2) - (altura // 2)
        janela.geometry(f"{largura}x{altura}+{x}+{y}")

    def criar_botoes_menu(self):
        estilo = ttk.Style()
        estilo.configure("TNotebook.Tab", font=("Arial", 9, "bold"), padding=[10, 4])
        
        self.abas_controle = ttk.Notebook(self.frame_menu)
        self.abas_controle.place(x=0, y=0, relwidth=1, height=30)
        
        aba_vendas = tk.Frame(self.abas_controle, bg="#dcdcdc")
        aba_estoque = tk.Frame(self.abas_controle, bg="#dcdcdc")
        aba_caixa = tk.Frame(self.abas_controle, bg="#dcdcdc")
        aba_financeiro = tk.Frame(self.abas_controle, bg="#dcdcdc")
        aba_relatorios = tk.Frame(self.abas_controle, bg="#dcdcdc")
        aba_config = tk.Frame(self.abas_controle, bg="#dcdcdc")
        
        self.abas_controle.add(aba_vendas, text=" 1 - VENDAS ")
        self.abas_controle.add(aba_estoque, text=" 2 - ESTOQUE ")
        self.abas_controle.add(aba_caixa, text=" 3 - CAIXA ")
        self.abas_controle.add(aba_financeiro, text=" 4 - FINANCEIRO ")
        self.abas_controle.add(aba_relatorios, text=" 5 - RELATÓRIOS ")
        self.abas_controle.add(aba_config, text=" 6 - CONFIGURAÇÃO DO SISTEMA ")
        
        self.frame_ferramentas = tk.Frame(self.frame_menu, bg="#f5f5f5", bd=1, relief="groove")
        self.frame_ferramentas.place(x=0, y=30, relwidth=1, height=80)
        
        def mudar_aba(event):
            aba_selecionada = self.abas_controle.index(self.abas_controle.select())
            if aba_selecionada == 0: 
                self.carregar_aba_vendas_inicial()
            elif aba_selecionada == 1: 
                self.carregar_ferramentas_estoque()
                self.acao_produtos()
            elif aba_selecionada == 2:
                self.carregar_ferramentas_caixa()
                self.acao_caixa()
            elif aba_selecionada == 3:
                self.carregar_ferramentas_padrao()
                self.acao_financeiro()
            elif aba_selecionada == 4:
                self.carregar_ferramentas_padrao()
                self.acao_relatorios()
            elif aba_selecionada == 5:
                self.carregar_ferramentas_configuracao()
                self.limpar_container()
                tk.Label(self.container_principal, text="Configurações do Sistema CUMMINS\nSelecione uma opção na barra de tarefas superior.", font=("Arial", 12), bg="#f0f0f0").pack(pady=100)
            else:
                self.carregar_ferramentas_padrao()
            
        self.abas_controle.bind("<<NotebookTabChanged>>", mudar_aba)

    def carregar_aba_vendas_inicial(self):
        self.carregar_ferramentas_vendas()
        self.limpar_container()
        self.barra_status.config(text=f"MÓDULO DE VENDAS | OPERADOR: {self.usuario_logado.upper()}")
        tk.Label(
            self.container_principal, 
            text="Módulo de Vendas Ativo.\nClique no botão 'MESAS' acima para carregar o mapa do salão.", 
            font=("Arial", 13, "italic"), 
            bg="#f0f0f0", 
            fg="#555555"
        ).pack(pady=150)

    def limpar_barra_ferramentas(self):
        for widget in self.frame_ferramentas.winfo_children():
            widget.destroy()

    def carregar_ferramentas_vendas(self):
        self.limpar_barra_ferramentas()
        botoes = [
            ("🪑", "MESAS", 10, self.acao_mesas),
            ("🌳", "PRAÇA", 105, lambda: messagebox.showinfo("Praça", "Exibindo mesas da Praça")),
            ("📑", "COMANDAS", 200, lambda: messagebox.showinfo("Comandas", "Painel de Comandas")),
            ("🍺", "BALCÃO", 295, lambda: messagebox.showinfo("Balcão", "Venda Balcão")),
            ("🖨️", "REIMPRIMIR\nCUPOM", 390, lambda: messagebox.showinfo("Cupom", "Cupom reimpresso")),
            ("📋", "DELIVERY", 485, self.acao_delivery),
            ("❌", "SAIR", 580, self.root.quit)
        ]
        self._renderizar_botoes(botoes)

    def carregar_ferramentas_estoque(self):
        self.limpar_barra_ferramentas()
        botoes = [
            ("📦", "ESTOQUE\nATUAL", 10, self.acao_produtos),
            ("➕", "ADICIONAR\nPRODUTOS", 105, self.janela_adicionar_produto),
            ("➖", "REMOVER\nPRODUTOS", 200, self.janela_remover_produto),
            ("🔄", "REAJUSTE\nESTOQUE", 295, self.janela_reajustar_estoque),
            ("❌", "SAIR", 390, self.root.quit)
        ]
        self._renderizar_botoes(botoes)

    def carregar_ferramentas_caixa(self):
        self.limpar_barra_ferramentas()
        botoes = [
            ("💰", "CAIXA\nATUAL", 10, self.acao_caixa),
            ("🔓", "ABERTURA\nDE CAIXA", 105, lambda: self.definir_movimentacao_caixa("Abertura")),
            ("🔒", "FECHAMENTO\nDE CAIXA", 200, lambda: self.definir_movimentacao_caixa("Fechamento")),
            ("📥", "SUPRIMENTO\n(ENTRADA)", 295, lambda: self.definir_movimentacao_caixa("Suprimento (Aporte)")),
            ("📤", "SANGRIA\n(SAIDA)", 390, lambda: self.definir_movimentacao_caixa("Sangria (Retirada)")),
            ("❌", "SAIR", 485, self.root.quit)
        ]
        self._renderizar_botoes(botoes)

    def carregar_ferramentas_configuracao(self):
        self.limpar_barra_ferramentas()
        botoes = [
            ("👤", "CADASTRAR\nOPERADOR", 10, self.janela_cadastrar_usuario),
            ("⚙️", "PARAMETROS", 105, lambda: messagebox.showinfo("Config", "Configurações gerais do sistema")),
            ("❌", "SAIR", 200, self.root.quit)
        ]
        self._renderizar_botoes(botoes)

    def carregar_ferramentas_padrao(self):
        self.limpar_barra_ferramentas()
        botoes = [
            ("⚙️", "CONFIGURAÇÃO", 10, lambda: messagebox.showinfo("Config", "Configurações")),
            ("📦", "ESTOQUE", 105, self.acao_produtos),
            ("💰", "CAIXA", 200, self.acao_caixa),
            ("❌", "SAIR", 295, self.root.quit)
        ]
        self._renderizar_botoes(botoes)

    def _renderizar_botoes(self, lista_botoes):
        for icone, texto, x_pos, comando in lista_botoes:
            btn = tk.Button(
                self.frame_ferramentas,
                text=f"{icone}\n{texto}",
                font=("Arial", 8, "bold"),
                bg="#f5f5f5",
                fg="#2c3e50",
                relief="flat",
                activebackground="#e6e6e6",
                bd=0,
                command=comando,
                justify="center"
            )
            if "SAIR" in texto:
                btn.config(fg="#c00000")
            btn.place(x=x_pos, y=5, width=95, height=65)

    def limpar_container(self):
        for widget in self.container_principal.winfo_children():
            widget.destroy()
    # ================= TELA: MAPA DE 40 MESAS =================
    def acao_mesas(self):
        self.limpar_container()
        self.barra_status.config(text="MAPA DE ATENDIMENTO DO SALÃO (40 MESAS) | OPERADOR: ADMIN")
        
        # Frame principal que preenche toda a área
        frame_grid = tk.Frame(self.container_principal, bg="#f0f0f0")
        frame_grid.pack(fill="both", expand=True, padx=20, pady=20)
        
        # --- ESSENCIAL: Configurar o peso para expandir ---
        # Configura as 8 colunas para terem o mesmo peso
        for col in range(8):
            frame_grid.columnconfigure(col, weight=1)
        # Configura as 5 linhas para terem o mesmo peso
        for row in range(5):
            frame_grid.rowconfigure(row, weight=1)
        
        mesas = banco.obter_todas_mesas()
        
        for i, (numero, status) in enumerate(mesas):
            cor = "#28a745" if status == "Disponível" else "#dc3545"
            
            # Botão
            btn = tk.Button(
                frame_grid, 
                text=f"Mesa {numero}\n{status}", 
                bg=cor, fg="white", 
                font=("Arial", 11, "bold") # Fonte um pouco maior
            )
            
            # Grid com sticky="nsew" para forçar o botão a preencher a célula
            btn.grid(
                row=i // 8, 
                column=i % 8, 
                padx=5, pady=5, 
                sticky="nsew"
            )
            
            # Comando de clique
            btn.config(command=lambda n=numero: self.gerenciar_mesa(n))
    def gerenciar_mesa(self, numero_mesa):
        status, valor = banco.obter_info_mesa(numero_mesa)
        
        if status == "Disponível":
            if not self.caixa_aberto:
                messagebox.showwarning("Caixa Fechado", "Caixa fechado! Realize a abertura antes de abrir mesas.")
                return
            if messagebox.askyesno("Abrir Mesa", f"Deseja abrir a {numero_mesa}?"):
                banco.abrir_mesa_banco(numero_mesa)
                self.acao_mesas()
                
            if messagebox.askyesno("Abrir Mesa", f"Deseja abrir a {numero_mesa}?"):
                banco.abrir_mesa_banco(numero_mesa)
                self.acao_mesas()
        else:
            # CRIAÇÃO DA JANELA POP-UP
            janela_opcoes = tk.Toplevel(self.root)
            janela_opcoes.title(f"Gerenciar - {numero_mesa}")
            
            # Centraliza perfeitamente a pop-up na tela
            self.centralizar_janela(janela_opcoes, 380, 340)
            janela_opcoes.resizable(False, False)
            janela_opcoes.grab_set()
            
            tk.Label(janela_opcoes, text=f"Gerenciando {numero_mesa}", font=("Arial", 12, "bold"), pady=10).pack()
            tk.Label(janela_opcoes, text=f"Consumo Atual: R$ {valor:.2f}", font=("Arial", 11, "bold"), fg="darkblue").pack(pady=5)
            tk.Label(janela_opcoes, text="Selecione o Produto para Lançar:", font=("Arial", 10)).pack(anchor="w", padx=25, pady=2)
            
            # Busca todos os produtos do estoque
            text_produtos = banco.listar_produtos()
            
            # CORREÇÃO AQUI: Lista os produtos cadastrados. 
            # Caso queira listar apenas o que tem estoque positivo, mantenha 'if prod[3] > 0'
            # Se quiser listar todos para teste, pode remover a validação temporariamente.
            produtos_disponiveis = [prod[1] for prod in text_produtos if prod[3] > 0]
            
            combo_produtos = ttk.Combobox(janela_opcoes, values=produtos_disponiveis, state="readonly", font=("Arial", 10))
            combo_produtos.pack(fill="x", padx=25, pady=5)
            
            if produtos_disponiveis:
                combo_produtos.current(0)
            else:
                # Caso o estoque esteja zerado, exibe um aviso e avisa o operador
                combo_produtos.config(state="disabled")
                lbl_aviso = tk.Label(janela_opcoes, text="* Nenhum produto com estoque disponível!", fg="red", font=("Arial", 9, "bold"))
                lbl_aviso.pack(pady=2)

            def executar_lancamento():
                produto_selecionado = combo_produtos.get()
                if not produto_selecionado:
                    messagebox.showwarning("Aviso", "Selecione um produto antes de lançar!", parent=janela_opcoes)
                    return
                sucesso, msg_ou_preco = banco.lancar_produto_na_mesa(numero_mesa, produto_selecionado)
                if sucesso:
                    messagebox.showinfo("Sucesso", f"{produto_selecionado} (R$ {msg_ou_preco:.2f}) lançado!", parent=janela_opcoes)
                    janela_opcoes.destroy()
                    self.acao_mesas()
                else:
                    messagebox.showerror("Erro", msg_ou_preco, parent=janela_opcoes)

            def fechar_conta():
                if messagebox.askyesno("Fechar Conta", f"Confirmar fechamento da {numero_mesa}?\nTotal: R$ {valor:.2f}", parent=janela_opcoes):
                    banco.fechar_mesa_banco(numero_mesa, valor)
                    janela_opcoes.destroy()
                    self.acao_mesas()

            tk.Button(janela_opcoes, text="Lançar Item Selecionado", bg="#ffc107", font=("Arial", 10, "bold"), command=executar_lancamento, width=25, height=2).pack(pady=15)
            tk.Button(janela_opcoes, text="Fechar Conta / Liberar Mesa", bg="#dc3545", fg="white", font=("Arial", 10, "bold"), command=fechar_conta, width=25, height=2).pack(pady=5)

            def executar_lancamento():
                produto_selecionado = combo_produtos.get()
                if not produto_selecionado:
                    messagebox.showwarning("Aviso", "Selecione um produto antes de lançar!")
                    return
                sucesso, msg_ou_preco = banco.lancar_produto_na_mesa(numero_mesa, produto_selecionado)
                if sucesso:
                    messagebox.showinfo("Sucesso", f"{produto_selecionado} (R$ {msg_ou_preco:.2f}) lançado!")
                    janela_opcoes.destroy()
                    self.acao_mesas()
                else:
                    messagebox.showerror("Erro", msg_ou_preco)

            def fechar_conta():
                if messagebox.askyesno("Fechar Conta", f"Confirmar fechamento da {numero_mesa}?\nTotal: R$ {valor:.2f}"):
                    banco.fechar_mesa_banco(numero_mesa, valor)
                    janela_opcoes.destroy()
                    self.acao_mesas()

            tk.Button(janela_opcoes, text="Lançar Item Selecionado", bg="#ffc107", font=("Arial", 10, "bold"), command=executar_lancamento, width=25, height=2).pack(pady=10)
            tk.Button(janela_opcoes, text="Fechar Conta / Liberar Mesa", bg="#dc3545", fg="white", font=("Arial", 10, "bold"), command=fechar_conta, width=25, height=2).pack(pady=5)

    # ================= TELA: DELIVERY =================
    def acao_delivery(self):
        self.limpar_container()
        self.barra_status.config(text="GESTÃO DE PEDIDOS - DELIVERY")
        
        frame_esq = tk.Frame(self.container_principal, bg="#f0f0f0", padx=15, pady=15, width=320)
        frame_esq.pack(side="left", fill="y")
        frame_esq.pack_propagate(False)
        
        frame_dir = tk.Frame(self.container_principal, bg="white", padx=15, pady=15)
        frame_dir.pack(side="right", fill="both", expand=True)
        
        tk.Label(frame_esq, text="Cliente:", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor="w", pady=2)
        entry_cliente = tk.Entry(frame_esq, font=("Arial", 10))
        entry_cliente.pack(fill="x", pady=5)
        
        tk.Label(frame_esq, text="Telefone:", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor="w", pady=2)
        entry_fone = tk.Entry(frame_esq, font=("Arial", 10))
        entry_fone.pack(fill="x", pady=5)
        
        tk.Label(frame_esq, text="Endereço de Entrega:", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor="w", pady=2)
        entry_end = tk.Entry(frame_esq, font=("Arial", 10))
        entry_end.pack(fill="x", pady=5)
        
        tk.Label(frame_esq, text="Valor total do Pedido (R$):", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor="w", pady=2)
        entry_total = tk.Entry(frame_esq, font=("Arial", 10))
        entry_total.pack(fill="x", pady=5)

        colunas = ("id", "cliente", "total", "status", "endereco")
        tabela_deliv = ttk.Treeview(frame_dir, columns=colunas, show="headings")
        tabela_deliv.heading("id", text="ID")
        tabela_deliv.heading("cliente", text="Cliente")
        tabela_deliv.heading("total", text="Total")
        tabela_deliv.heading("status", text="Status")
        tabela_deliv.heading("endereco", text="Endereço")
        
        tabela_deliv.column("id", width=40, anchor="center")
        tabela_deliv.column("cliente", width=120, anchor="w")
        tabela_deliv.column("total", width=80, anchor="center")
        tabela_deliv.column("status", width=90, anchor="center")
        tabela_deliv.column("endereco", width=180, anchor="w")
        tabela_deliv.pack(fill="both", expand=True)

        def atualizar_tabela_deliv():
            for row in tabela_deliv.get_children(): tabela_deliv.delete(row)
            for ped in banco.listar_deliveries():
                tabela_deliv.insert("", "end", values=(ped[0], ped[1], f"R$ {ped[2]:.2f}", ped[3], ped[4]))

        def cadastrar_delivery():
            try:
                tot = float(entry_total.get().replace(",", "."))
                banco.lancar_delivery(entry_cliente.get(), entry_fone.get(), entry_end.get(), 0.0, tot)
                messagebox.showinfo("Sucesso", "Pedido de Delivery Cadastrado!")
                atualizar_tabela_deliv()
                entry_cliente.delete(0, tk.END); entry_fone.delete(0, tk.END); entry_end.delete(0, tk.END); entry_total.delete(0, tk.END)
            except ValueError: messagebox.showerror("Erro", "Insira um valor numérico válido.")

        def mudar_status():
            selecionado = tabela_deliv.selection()
            if not selecionado: 
                messagebox.showwarning("Aviso", "Selecione um pedido para alterar o status.")
                return
            item = tabela_deliv.item(selecionado)['values']
            
            janela_status = tk.Toplevel(self.root)
            janela_status.title("Atualizar Status")
            
            self.centralizar_janela(janela_status, 250, 150)
            janela_status.grab_set()
            
            tk.Label(janela_status, text="Selecione o novo Status:", font=("Arial", 10)).pack(pady=10)
            combo = ttk.Combobox(janela_status, values=["Pendente", "Em Rota", "Entregue"], state="readonly")
            combo.pack(pady=5)
            combo.current(0)
            
            def salvar_status():
                banco.atualizar_status_delivery(item[0], combo.get())
                janela_status.destroy()
                atualizar_tabela_deliv()
                
            tk.Button(janela_status, text="Salvar", bg="#28a745", fg="white", command=salvar_status).pack(pady=10)

        tk.Button(frame_esq, text="Lançar Novo Delivery", bg="#28a745", fg="white", font=("Arial", 10, "bold"), command=cadastrar_delivery).pack(fill="x", pady=10)
        tk.Button(frame_esq, text="Mudar Status do Pedido", bg="#007bff", fg="white", font=("Arial", 10, "bold"), command=mudar_status).pack(fill="x", pady=5)
        atualizar_tabela_deliv()

    # ================= TELA: CAIXA =================
    def acao_caixa(self):
        self.limpar_container()
        self.barra_status.config(text="CONTROLE DE FLUXO DE CAIXA DIÁRIO")
        
        frame_esq = tk.Frame(self.container_principal, bg="#f0f0f0", padx=15, pady=15, width=300)
        frame_esq.pack(side="left", fill="y")
        frame_esq.pack_propagate(False)
        
        frame_dir = tk.Frame(self.container_principal, bg="white", padx=15, pady=15)
        frame_dir.pack(side="right", fill="both", expand=True)
        
        cor_status = "#28a745" if self.caixa_aberto else "#dc3545"
        texto_status = "CAIXA ABERTO" if self.caixa_aberto else "CAIXA FECHADO"
        lbl_info = tk.Label(frame_esq, text=texto_status, font=("Arial", 12, "bold"), bg=cor_status, fg="white", pady=8)
        lbl_info.pack(fill="x", pady=5)

        tk.Label(frame_esq, text="Tipo de Movimentação:", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor="w", pady=10)
        self.combo_tipo = ttk.Combobox(frame_esq, values=["Abertura", "Sangria (Retirada)", "Suprimento (Aporte)", "Fechamento"], state="readonly")
        self.combo_tipo.pack(fill="x", pady=2)
        self.combo_tipo.current(0)
        
        tk.Label(frame_esq, text="Valor (R$):", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor="w", pady=8)
        self.entry_val = tk.Entry(frame_esq, font=("Arial", 10))
        self.entry_val.pack(fill="x", pady=2)
        
        tk.Label(frame_esq, text="Descrição / Motivo:", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor="w", pady=8)
        self.entry_desc = tk.Entry(frame_esq, font=("Arial", 10))
        self.entry_desc.pack(fill="x", pady=2)

        colunas = ("tipo", "valor", "desc", "horario")
        self.tabela_caixa = ttk.Treeview(frame_dir, columns=colunas, show="headings")
        self.tabela_caixa.heading("tipo", text="Tipo")
        self.tabela_caixa.heading("valor", text="Valor")
        self.tabela_caixa.heading("desc", text="Descrição")
        self.tabela_caixa.heading("horario", text="Horário")
        
        self.tabela_caixa.column("tipo", width=120, anchor="center")
        self.tabela_caixa.column("valor", width=90, anchor="center")
        self.tabela_caixa.column("desc", width=200, anchor="w")
        self.tabela_caixa.column("horario", width=130, anchor="center")
        self.tabela_caixa.pack(fill="both", expand=True)

        def lancar_mov():
            try:
                v = float(self.entry_val.get().replace(",", "."))
                tipo = self.combo_tipo.get()
                
                if tipo == "Abertura" and self.caixa_aberto:
                    messagebox.showwarning("Aviso", "O caixa já está aberto!")
                    return
                
                banco.lancar_movimentacao_caixa(tipo, v, self.entry_desc.get())
                
                if tipo == "Fechamento":
                    self.caixa_aberto = False
                else:
                    self.caixa_aberto = True
                    
                messagebox.showinfo("Sucesso", "Movimentação registrada com sucesso!")
                self.atualizar_caixa()
                self.entry_val.delete(0, tk.END)
                self.entry_desc.delete(0, tk.END)
                
                self.acao_caixa()
            except ValueError: 
                messagebox.showerror("Erro", "Insira um valor numérico válido.")

        tk.Button(frame_esq, text="Registrar Movimentação", bg="#2c3e50", fg="white", font=("Arial", 10, "bold"), command=lancar_mov).pack(fill="x", pady=20)
        self.atualizar_caixa()

    def atualizar_caixa(self):
        if hasattr(self, 'tabela_caixa') and self.tabela_caixa.winfo_exists():
            for row in self.tabela_caixa.get_children(): self.tabela_caixa.delete(row)
            for mov in banco.obter_fluxo_caixa_dia():
                self.tabela_caixa.insert("", "end", values=(mov[0], f"R$ {mov[1]:.2f}", mov[2], mov[3]))

    def definir_movimentacao_caixa(self, tipo_selecionado):
        self.acao_caixa()
        self.combo_tipo.set(tipo_selecionado)
        self.entry_desc.focus()

    # ================= TELA: FINANCEIRO =================
    def acao_financeiro(self):
        self.limpar_container()
        self.barra_status.config(text="GESTÃO FINANCEIRA (CONTAS A PAGAR / RECEBER)")
        
        frame_esq = tk.Frame(self.container_principal, bg="#f0f0f0", padx=15, pady=15, width=300)
        frame_esq.pack(side="left", fill="y")
        frame_esq.pack_propagate(False)
        
        frame_dir = tk.Frame(self.container_principal, bg="white", padx=15, pady=15)
        frame_dir.pack(side="right", fill="both", expand=True)
        
        tk.Label(frame_esq, text="Fluxo da Conta:", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor="w", pady=2)
        combo_f = ttk.Combobox(frame_esq, values=["Pagar", "Receber"], state="readonly")
        combo_f.pack(fill="x", pady=5)
        combo_f.current(0)
        
        tk.Label(frame_esq, text="Descrição (Ex: Aluguel, Internet):", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor="w", pady=2)
        entry_d = tk.Entry(frame_esq, font=("Arial", 10))
        entry_d.pack(fill="x", pady=5)
        
        tk.Label(frame_esq, text="Valor (R$):", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor="w", pady=2)
        entry_v = tk.Entry(frame_esq, font=("Arial", 10))
        entry_v.pack(fill="x", pady=5)
        
        tk.Label(frame_esq, text="Vencimento (AAAA-MM-DD):", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(anchor="w", pady=2)
        entry_dt = tk.Entry(frame_esq, font=("Arial", 10))
        entry_dt.pack(fill="x", pady=5)

        colunas = ("id", "tipo", "desc", "valor", "venc", "status")
        tabela_fin = ttk.Treeview(frame_dir, columns=colunas, show="headings")
        tabela_fin.heading("id", text="ID")
        tabela_fin.heading("tipo", text="Tipo")
        tabela_fin.heading("desc", text="Descrição")
        tabela_fin.heading("valor", text="Valor")
        tabela_fin.heading("venc", text="Vencimento")
        tabela_fin.heading("status", text="Status")
        
        tabela_fin.column("id", width=30, anchor="center")
        tabela_fin.column("tipo", width=70, anchor="center")
        tabela_fin.column("desc", width=150, anchor="w")
        tabela_fin.column("valor", width=80, anchor="center")
        tabela_fin.column("venc", width=90, anchor="center")
        tabela_fin.column("status", width=80, anchor="center")
        tabela_fin.pack(fill="both", expand=True)

        def atualizar_fin():
            for row in tabela_fin.get_children(): tabela_fin.delete(row)
            for c in banco.listar_contas():
                tabela_fin.insert("", "end", values=(c[0], c[1], c[2], f"R$ {c[3]:.2f}", c[4], c[5]))

        def cadastrar_conta():
            try:
                val = float(entry_v.get().replace(",", "."))
                banco.lancar_conta(combo_f.get(), entry_d.get(), val, entry_dt.get())
                messagebox.showinfo("Sucesso", "Lançamento Financeiro Registrado!")
                atualizar_fin()
                entry_d.delete(0, tk.END); entry_v.delete(0, tk.END); entry_dt.delete(0, tk.END)
            except ValueError: messagebox.showerror("Erro", "Verifique as informações digitadas.")

        def pagar_conta():
            sel = tabela_fin.selection()
            if not sel: 
                messagebox.showwarning("Aviso", "Selecione uma conta para dar baixa.")
                return
            item = tabela_fin.item(sel)['values']
            if messagebox.askyesno("Confirmar", f"Confirmar baixa da conta ID {item[0]}?"):
                banco.baixar_conta(item[0])
                atualizar_fin()

        tk.Button(frame_esq, text="Salvar Conta", bg="#28a745", fg="white", font=("Arial", 10, "bold"), command=cadastrar_conta).pack(fill="x", pady=10)
        tk.Button(frame_esq, text="Dar Baixa (Marcar como Pago)", bg="#ffc107", font=("Arial", 10, "bold"), command=pagar_conta).pack(fill="x", pady=5)
        atualizar_fin()

    # ================= TELA: GESTÃO DO ESTOQUE (PRODUTOS) =============
    def acao_produtos(self):
        self.limpar_container()
        self.barra_status.config(text="CONTROLE DE ESTOQUE - LISTAGEM DE PRODUTOS")
        
        frame_tabela = tk.Frame(self.container_principal, bg="white", padx=15, pady=15)
        frame_tabela.pack(fill="both", expand=True)
        
        colunas = ("id", "nome", "preco", "qtd")
        self.tabela_produtos = ttk.Treeview(frame_tabela, columns=colunas, show="headings")
        self.tabela_produtos.heading("id", text="ID")
        self.tabela_produtos.heading("nome", text="Nome do Produto")
        self.tabela_produtos.heading("preco", text="Preço (R$)")
        self.tabela_produtos.heading("qtd", text="Qtd em Estoque")
        
        self.tabela_produtos.column("id", width=60, anchor="center")
        self.tabela_produtos.column("nome", width=400, anchor="w")
        self.tabela_produtos.column("preco", width=120, anchor="center")
        self.tabela_produtos.column("qtd", width=100, anchor="center")
        self.tabela_produtos.pack(fill="both", expand=True)
        
        self.atualizar_tabela_produtos()

    def atualizar_tabela_produtos(self):
        if hasattr(self, 'tabela_produtos') and self.tabela_produtos.winfo_exists():
            for row in self.tabela_produtos.get_children():
                self.tabela_produtos.delete(row)
            for prod in banco.listar_produtos():
                self.tabela_produtos.insert("", "end", values=(prod[0], prod[1], f"R$ {prod[2]:.2f}", prod[3]))

    def janela_adicionar_produto(self):
        janela = tk.Toplevel(self.root)
        janela.title("Cadastrar Novo Produto")
        self.centralizar_janela(janela, 340, 280)
        janela.resizable(False, False)
        janela.grab_set()

        tk.Label(janela, text="Nome do Produto:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=5)
        en_nome = tk.Entry(janela, font=("Arial", 10))
        en_nome.pack(fill="x", padx=20)

        tk.Label(janela, text="Preço de Venda (R$):", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=5)
        en_preco = tk.Entry(janela, font=("Arial", 10))
        en_preco.pack(fill="x", padx=20)

        tk.Label(janela, text="Quantidade Inicial:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=5)
        en_qtd = tk.Entry(janela, font=("Arial", 10))
        en_qtd.pack(fill="x", padx=20)

        def salvar():
            nome = en_nome.get().strip()
            try:
                preco = float(en_preco.get().replace(",", "."))
                qtd = int(en_qtd.get())
                if nome == "": raise ValueError
                if banco.adicionar_produto(nome, preco, qtd):
                    messagebox.showinfo("Sucesso", f"'{nome}' cadastrado!", parent=janela)
                    janela.destroy()
                    self.atualizar_tabela_produtos()
                else:
                    messagebox.showerror("Erro", "Produto já existe.", parent=janela)
            except ValueError:
                messagebox.showerror("Erro", "Preencha os dados corretamente.", parent=janela)

        tk.Button(janela, text="Salvar Produto", bg="#28a745", fg="white", font=("Arial", 10, "bold"), command=salvar).pack(fill="x", padx=20, pady=20)

    def janela_remover_produto(self):
        id_inicial = ""
        nome_inicial = ""
        try:
            sel = self.tabela_produtos.selection()
            if sel:
                valores = self.tabela_produtos.item(sel)['values']
                id_inicial = valores[0]
                nome_inicial = valores[1]
        except: pass

        janela = tk.Toplevel(self.root)
        janela.title("Remover Produto")
        self.centralizar_janela(janela, 340, 220)
        janela.resizable(False, False)
        janela.grab_set()

        tk.Label(janela, text="Para remover, digite ou selecione o ID do produto:", font=("Arial", 9)).pack(anchor="w", padx=20, pady=5)
        
        tk.Label(janela, text="ID do Produto:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=2)
        en_id = tk.Entry(janela, font=("Arial", 10))
        en_id.pack(fill="x", padx=20)
        if id_inicial: en_id.insert(0, id_inicial)

        lbl_nome = tk.Label(janela, text=f"Selecionado: {nome_inicial}" if nome_inicial else "", font=("Arial", 9, "italic"), fg="gray")
        lbl_nome.pack(anchor="w", padx=20, pady=5)

        def deletar():
            id_p = en_id.get().strip()
            if not id_p:
                messagebox.showwarning("Aviso", "Informe um ID válido.", parent=janela)
                return
            if messagebox.askyesno("Confirmar Exclusão", f"Confirmar exclusão permanente do produto ID {id_p}?", parent=janela):
                banco.remover_produto(id_p)
                messagebox.showinfo("Sucesso", "Ação concluída!", parent=janela)
                janela.destroy()
                self.atualizar_tabela_produtos()

        tk.Button(janela, text="Remover Permanentemente", bg="#dc3545", fg="white", font=("Arial", 10, "bold"), command=deletar).pack(fill="x", padx=20, pady=15)

    def janela_reajustar_estoque(self):
        id_inicial = ""
        try:
            sel = self.tabela_produtos.selection()
            if sel: id_inicial = self.tabela_produtos.item(sel)['values'][0]
        except: pass

        janela = tk.Toplevel(self.root)
        janela.title("Ajustar / Editar Produto")
        self.centralizar_janela(janela, 340, 300)
        janela.resizable(False, False)
        janela.grab_set()

        tk.Label(janela, text="ID do Produto para Alterar:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=5)
        en_id = tk.Entry(janela, font=("Arial", 10))
        en_id.pack(fill="x", padx=20)
        if id_inicial: en_id.insert(0, id_inicial)

        tk.Label(janela, text="Novo Nome:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=5)
        en_nome = tk.Entry(janela, font=("Arial", 10))
        en_nome.pack(fill="x", padx=20)

        tk.Label(janela, text="Novo Preço (R$):", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=5)
        en_preco = tk.Entry(janela, font=("Arial", 10))
        en_preco.pack(fill="x", padx=20)

        tk.Label(janela, text="Nova Qtd Estoque:", font=("Arial", 10, "bold")).pack(anchor="w", padx=20, pady=5)
        en_qtd = tk.Entry(janela, font=("Arial", 10))
        en_qtd.pack(fill="x", padx=20)

        def aplicar():
            id_p = en_id.get().strip()
            nome = en_nome.get().strip()
            try:
                preco = float(en_preco.get().replace(",", "."))
                qtd = int(en_qtd.get())
                if nome == "" or id_p == "": raise ValueError
                banco.alterar_produto(id_p, nome, preco, qtd)
                messagebox.showinfo("Sucesso", "Produto updated!", parent=janela)
                janela.destroy()
                self.atualizar_tabela_produtos()
            except ValueError:
                messagebox.showerror("Erro", "Certifique-se de preencher todos os campos.", parent=janela)

        tk.Button(janela, text="Salvar Alterações", bg="#ffc107", font=("Arial", 10, "bold"), command=aplicar).pack(fill="x", padx=20, pady=15)

    # ================= TELA: RELATÓRIOS DIÁRIOS =================
    def acao_relatorios(self):
        self.limpar_container()
        self.barra_status.config(text="RELATÓRIO DE MOVIMENTAÇÃO DIÁRIA")
        
        frame_conteudo = tk.Frame(self.container_principal, bg="#f0f0f0", padx=30, pady=20)
        frame_conteudo.pack(fill="both", expand=True)
        
        colunas = ("mesa", "valor", "horario")
        tabela_vendas = ttk.Treeview(frame_conteudo, columns=colunas, show="headings")
        tabela_vendas.heading("mesa", text="Origem/Mesa")
        tabela_vendas.heading("valor", text="Faturamento")
        tabela_vendas.heading("horario", text="Data / Horário")
        
        tabela_vendas.column("mesa", width=150, anchor="center")
        tabela_vendas.column("valor", width=200, anchor="center")
        tabela_vendas.column("horario", width=300, anchor="center")
        tabela_vendas.pack(fill="both", expand=True, pady=10)
        
        vendas = banco.obter_vendas_do_dia()
        faturamento_total = 0.0
        
        for v in vendas:
            tabela_vendas.insert("", "end", values=(v[0], f"R$ {v[1]:.2f}", v[2]))
            faturamento_total += v[1]
            
        frame_resumo = tk.Frame(frame_conteudo, bg="#e2e3e5", bd=2, relief="groove", pady=15)
        frame_resumo.pack(fill="x", side="bottom")
        
        lbl_faturamento = tk.Label(frame_resumo, text=f"TOTAL FATURADO HOJE: R$ {faturamento_total:.2f}", font=("Arial", 14, "bold"), bg="#e2e3e5", fg="#155724")
        lbl_faturamento.pack()
        
        lbl_atendimentos = tk.Label(frame_resumo, text=f"Total de Atendimentos: {len(vendas)} registros encerrados.", font=("Arial", 11), bg="#e2e3e5")
        lbl_atendimentos.pack()

# --- EXECUÇÃO ---
if __name__ == "__main__":
    banco.inicializar_banco()
    root = tk.Tk()
    app = AplicativoRestaurante(root)
    root.mainloop()