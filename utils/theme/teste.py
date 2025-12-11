import tkinter as tk

root = tk.Tk()

# Remove completamente a barra de título e as bordas da janela
#root.overrideredirect(True) 

root.geometry("400x200")
root.configure(bg="white")

label = tk.Label(root, text="Janela Sem Título, Bordas ou Ícone", bg="white")
label.pack(pady=50)

# Já que a barra de título se foi, forneça um botão para fechar a janela
close_button = tk.Button(root, text="Fechar", command=root.destroy)
close_button.pack(pady=20)

# Você precisará de código extra para permitir que o usuário arraste esta janela
# (não incluído aqui para simplificar, mas necessário para usabilidade)

root.mainloop()
