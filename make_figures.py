"""Publication figures from recorded data. Run with .venv/bin/python."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
ROOT=Path(__file__).resolve().parent
BG='#fbf8f2';INK='#172a34';MUTED='#627078';ORANGE='#e6653a';GREEN='#148474';BLUE='#4a7298';GOLD='#bd9841'
COLORS=[INK,BLUE,GOLD,GREEN]
NAMES=['GPT-5.1\nmedium','DeepSeek V4\nFlash','Kimi K2.6','Jev router']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.facecolor':BG,'figure.facecolor':BG,'text.color':INK,'axes.labelcolor':INK,'xtick.color':MUTED,'ytick.color':MUTED,'axes.edgecolor':MUTED,'svg.fonttype':'none'})
def save(fig,name):
    fig.savefig(ROOT/'figures'/f'{name}.png',dpi=180,bbox_inches='tight',facecolor=BG)
    fig.savefig(ROOT/'figures'/f'{name}.svg',bbox_inches='tight',facecolor=BG)
    plt.close(fig)
def clean(ax):
    ax.spines[['top','right','left']].set_visible(False);ax.tick_params(length=0);ax.grid(axis='y',alpha=.13);ax.set_axisbelow(True)
def box(ax,x,y,w,h,title,desc,color=GREEN):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012,rounding_size=0.025',facecolor=BG,edgecolor=color,linewidth=2))
    ax.text(x+w/2,y+h*.65,title,ha='center',va='center',weight='bold',fontsize=14,color=color)
    ax.text(x+w/2,y+h*.28,desc,ha='center',va='center',fontsize=10,color=MUTED)
def arrow(ax,a,b,color=MUTED):ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=18,linewidth=1.8,color=color))
def main():
    finaldir='confirmation' if (ROOT/'confirmation/results/summary.json').exists() else 'core'
    s=json.loads((ROOT/finaldir/'results/summary.json').read_text());a=s['arms'];order=['openai','small','large','routed']
    fig,ax=plt.subplots(figsize=(12,5.5));ax.axis('off');ax.set_xlim(0,1);ax.set_ylim(0,1)
    ax.text(.02,.96,'A small decision before a bigger answer',fontsize=24,weight='bold')
    box(ax,.025,.36,.18,.27,'User request','Text + constraints',INK)
    box(ax,.29,.36,.22,.27,'Jev','Typed routing signals',GREEN)
    box(ax,.61,.63,.35,.23,'DeepSeek V4 Flash','Routine structured text · lower cost',BLUE)
    box(ax,.61,.15,.35,.23,'Kimi K2.6','Complex or uncertain requests',GOLD)
    arrow(ax,(.205,.495),(.29,.495));arrow(ax,(.51,.53),(.61,.745),BLUE);arrow(ax,(.51,.46),(.61,.265),GOLD)
    ax.text(.545,.81,'cheap / sufficient',fontsize=10,color=BLUE)
    ax.text(.54,.1,'complexity or uncertainty → stronger model',fontsize=10,color=GOLD)
    ax.text(.025,.025,'Jev chooses the tier. The selected open model generates the answer. Routing cost is included.',fontsize=11,color=MUTED)
    save(fig,'architecture')
    fig,axes=plt.subplots(1,2,figsize=(12,5.4));cost=[a[x]['cost_usd'] for x in order];quality=[100*a[x]['objective_pass_rate'] for x in order]
    for ax in axes:clean(ax)
    axes[0].bar(NAMES,cost,color=COLORS,width=.6,yerr=[[0]*4,[a[x]['cost_upper_usd']-a[x]['cost_usd'] for x in order]],capsize=5);axes[0].set_ylabel('USD · 90 requests');axes[0].set_title('What the same workload costs',loc='left',weight='bold',pad=24)
    for i,v in enumerate(cost):axes[0].text(i,v+max(cost)*.025,f'${v:.4f}',ha='center',fontsize=10)
    axes[0].set_ylim(0,max(a[x]['cost_upper_usd'] for x in order)*1.2)
    errlo=[quality[i]-100*a[x]['objective_ci95_task_bootstrap'][0] for i,x in enumerate(order)];errhi=[100*a[x]['objective_ci95_task_bootstrap'][1]-quality[i] for i,x in enumerate(order)]
    axes[1].bar(NAMES,quality,color=COLORS,width=.6,yerr=[errlo,errhi],capsize=5);axes[1].set_ylabel('Objective success (%)');axes[1].set_title('What it gets right',loc='left',weight='bold',pad=24);axes[1].set_ylim(0,115)
    for i,v in enumerate(quality):axes[1].text(i,106,f'{a[order[i]]["objective_passes"]}/90',ha='center',fontsize=11,weight='bold')
    fig.text(.08,.01,'30 fresh structured-text tasks × 3 repeats. Error bars: 95% task-cluster bootstrap intervals.',fontsize=10,color=MUTED);fig.tight_layout(rect=(0,.04,1,1));save(fig,'cost-quality')
    fig,ax=plt.subplots(figsize=(11,5.2));clean(ax)
    rr=json.loads((ROOT/finaldir/'results/scored.json').read_text());cheap=sum(r['arm']=='routed' and 'DeepSeek' in (r['model'] or '') for r in rr);strong=sum(r['arm']=='routed' and 'Kimi' in (r['model'] or '') for r in rr);failed=90-cheap-strong
    ax.barh(['Routed requests'],[cheap],color=BLUE,height=.32,label='DeepSeek V4 Flash');ax.barh(['Routed requests'],[strong],left=[cheap],color=GOLD,height=.32,label='Kimi K2.6')
    if failed:ax.barh(['Routed requests'],[failed],left=[cheap+strong],color=MUTED,height=.32,label='No generation response')
    if cheap:ax.text(cheap/2,0,f'{cheap} cheaper-model calls',ha='center',va='center',color='white',weight='bold')
    if strong:ax.text(cheap+strong/2,0,f'{strong} stronger-model calls',ha='center',va='center',color=INK,weight='bold')
    ax.set_xlim(0,90);ax.set_xlabel('Calls');ax.set_title('Where Jev sent the work',loc='left',fontsize=22,weight='bold',pad=25);ax.legend(loc='upper center',bbox_to_anchor=(.5,-.2),ncol=2,frameon=False);ax.set_ylim(-.6,.6);fig.tight_layout();save(fig,'routing')
    fig,ax=plt.subplots(figsize=(11,5.3));clean(ax)
    cats=list(a['routed']['by_category']);xx=list(range(len(cats)));width=.19
    for j,key in enumerate(order):ax.bar([x+(j-1.5)*width for x in xx],[100*a[key]['by_category'][c] for c in cats],width=width,color=COLORS[j],label=NAMES[j].replace('\n',' '))
    ax.set_xticks(xx,[x.replace('_',' ').title() for x in cats]);ax.set_ylim(0,115);ax.set_ylabel('Success (%)');ax.set_title('Does the result hold across the chosen workload?',loc='left',fontsize=19,weight='bold',pad=24);ax.legend(loc='upper center',bbox_to_anchor=(.5,-.1),ncol=2,frameon=False);fig.tight_layout();save(fig,'categories')
    d=json.loads((ROOT/'results/summary.json').read_text())
    fig,ax=plt.subplots(figsize=(11,5.3));clean(ax)
    cats=['extraction','coding','reasoning','data'];values=[100*d['arms']['routed']['by_category'][c] for c in cats]
    ax.bar(cats,values,color=[GREEN,MUTED,MUTED,ORANGE],width=.55)
    for i,v in enumerate(values):ax.text(i,v+3,f'{v:.1f}%',ha='center',weight='bold')
    ax.set_ylim(0,110);ax.set_ylabel('Objective success (%)');ax.set_title('Discovery: structured text was the promising category',loc='left',fontsize=20,weight='bold',pad=22)
    fig.text(.09,.02,'Initial Qwen portfolio, 6 tasks per category × 3 repeats. Revised portfolio tested separately.',fontsize=10,color=MUTED);fig.tight_layout(rect=(0,.04,1,1));save(fig,'discovery')
    fig,ax=plt.subplots(figsize=(10,5.5));clean(ax)
    xx=[a[k]['cost_usd']/90*1000 for k in order];yy=[100*a[k]['objective_pass_rate'] for k in order]
    for i,k in enumerate(order):ax.scatter(xx[i],yy[i],s=160,color=COLORS[i],edgecolor=BG,linewidth=2,zorder=3);ax.annotate(NAMES[i].replace('\n',' '),(xx[i],yy[i]),xytext=(6,[-30,-17,12,27][i]),textcoords='offset points',fontsize=11)
    ax.set_xscale('log');ax.set_ylim(max(0,min(yy)-10),105);ax.set_xlim(min(xx)*.6,max(xx)*1.6);ax.set_xlabel('USD per 1,000 requests · log scale, workload projection');ax.set_ylabel('Objective success (%)');ax.set_title('The cost–quality frontier',loc='left',fontsize=22,weight='bold',pad=25);fig.tight_layout();save(fig,'frontier')
if __name__=='__main__':main()
